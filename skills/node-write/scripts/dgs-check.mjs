#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { createHash, randomUUID } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

export const sha256 = (bytes) => createHash('sha256').update(bytes).digest('hex');
export const canonical = (value) => {
  const resolved = path.resolve(value);
  return process.platform === 'win32' ? resolved.toLowerCase() : resolved;
};
export function extension(value) {
  const name = path.basename(value).toLowerCase();
  return name.endsWith('.d.ts') ? '.d.ts' : path.extname(name) || (/^\.[^.]+$/.test(name) ? name : '');
}
export function fingerprint(executable) {
  if (!path.isAbsolute(executable)) throw new Error('运行时和观察器必须使用绝对路径');
  const real = fs.realpathSync(executable);
  return { path: real, sha256: sha256(fs.readFileSync(real)) };
}
export function inspect(observer, target) {
  if (!path.isAbsolute(observer) || !path.isAbsolute(target)) throw new Error('观察器和目标必须使用绝对路径');
  const result = spawnSync(observer, [target], {
    encoding: 'utf8', timeout: 10000, maxBuffer: 65536, windowsHide: true,
  });
  if (result.error || result.status !== 0) throw new Error('独立观察器不可用或读取失败');
  let physical;
  try { physical = JSON.parse(result.stdout.trim()); } catch { throw new Error('观察器输出不是有效 JSON'); }
  if (!/^(?:[a-f0-9]{2}){0,16}$/i.test(physical.headerHex)
      || !/^[a-f0-9]{64}$/i.test(physical.sha256)
      || !Number.isSafeInteger(physical.bytes) || physical.bytes < 0) {
    throw new Error('观察器输出缺少有效文件头、长度或 SHA-256');
  }
  return physical;
}
function cipherPrefix(value) {
  if (!/^(?:[a-f0-9]{2}){4,16}$/i.test(value ?? '')) throw new Error('密文标识须为已验证的 4–16 字节十六进制前缀');
  return value.toUpperCase();
}
export function verifyCipher(observer, target, prefix, plaintext) {
  const expected = cipherPrefix(prefix);
  let physical;
  for (let attempt = 0; attempt < 4; attempt++) {
    physical = inspect(observer, target);
    if (physical.headerHex.toUpperCase().startsWith(expected) && physical.sha256 !== sha256(plaintext)) return physical;
    if (attempt < 3) Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 100);
  }
  throw new Error('独立视角未确认预期密文；检查目标实际状态，不能认定已加密或已回滚');
}
export function validateEvidence(evidencePath, observer, target) {
  if (!path.isAbsolute(evidencePath)) throw new Error('DGS 证据必须使用绝对路径');
  let evidence;
  try { evidence = JSON.parse(fs.readFileSync(evidencePath, 'utf8').replace(/^\uFEFF/, '')); }
  catch { throw new Error('无法读取 DGS 探针证据'); }
  const runtime = fingerprint(process.execPath), watcher = fingerprint(observer);
  if (evidence.version !== 1 || evidence.verified !== 'node-readback+independent-cipher'
      || evidence.runtime?.sha256 !== runtime.sha256 || canonical(evidence.runtime?.path ?? '') !== canonical(runtime.path)
      || evidence.observer?.sha256 !== watcher.sha256 || canonical(evidence.observer?.path ?? '') !== canonical(watcher.path)
      || canonical(evidence.directory ?? '') !== canonical(fs.realpathSync(path.dirname(target)))
      || evidence.extension !== extension(target)) {
    throw new Error('DGS 证据与当前运行时、观察器、目标目录或后缀不符；重新运行同目录探针');
  }
  if (!Number.isFinite(Date.parse(evidence.createdAt))) throw new Error('DGS 证据缺少有效验证时间');
  return { ...evidence, cipherPrefix: cipherPrefix(evidence.cipherPrefix) };
}

function probe(options) {
  const directory = options['--directory'];
  const suffix = options['--extension'];
  const observer = options['--observer'];
  if (!directory || !path.isAbsolute(directory)) throw new Error('探针目录必须是已存在的绝对路径');
  if (!/^\.[a-z0-9]+(?:\.[a-z0-9]+)*$/i.test(suffix ?? '')) throw new Error('后缀无效');
  if (!observer) throw new Error('需要独立观察器的绝对路径');
  const prefix = cipherPrefix(options['--cipher-prefix']);
  const runtime = fingerprint(process.execPath), watcher = fingerprint(observer);
  const resolvedDirectory = fs.realpathSync(directory);
  const target = path.join(resolvedDirectory, `codex-dgs-probe-${randomUUID()}${suffix}`);
  const payload = Buffer.from('Codex DGS probe\r\nUTF-8 中文验证\r\nNo business data\r\n');
  let created = false;
  try {
    fs.writeFileSync(target, payload, { flag: 'wx' });
    created = true;
    if (!fs.readFileSync(target).equals(payload)) throw new Error('探针明文读回不一致');
    const physical = verifyCipher(observer, target, prefix, payload);
    const evidence = {
      version: 1, verified: 'node-readback+independent-cipher', createdAt: new Date().toISOString(),
      runtime, observer: watcher, directory: resolvedDirectory, extension: extension(target), cipherPrefix: prefix,
      plaintextSha256: sha256(payload), physical,
    };
    if (options['--out']) {
      const out = options['--out'];
      if (!path.isAbsolute(out) || path.extname(out).toLowerCase() !== '.txt') throw new Error('证据输出须为绝对 .txt 路径');
      const serialized = Buffer.from(`${JSON.stringify(evidence, null, 2)}\n`);
      fs.writeFileSync(out, serialized, { flag: 'wx' });
      if (!fs.readFileSync(out).equals(serialized)) throw new Error('证据读回失败');
    }
    console.log(JSON.stringify({ ok: true, ...evidence, evidenceFile: options['--out'] ?? null }));
  } finally {
    // Remove only the exact random probe successfully created by this invocation.
    if (created) fs.unlinkSync(target);
  }
}

const usage = 'node dgs-check.mjs probe --directory <absolute-dir> --extension .ts '
  + '--observer <absolute-executable> --cipher-prefix <verified-hex> [--out <absolute.txt>]';
if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) {
  try {
    const [command, ...args] = process.argv.slice(2);
    if (command === '--help' && !args.length) console.log(usage);
    else {
      if (command !== 'probe') throw new Error(usage);
      const options = {};
      for (let i = 0; i < args.length; i++) {
        const key = args[i], value = args[++i];
        if (!['--directory', '--extension', '--observer', '--cipher-prefix', '--out'].includes(key)
            || Object.hasOwn(options, key) || !value || value.startsWith('--')) throw new Error('未知、重复或缺值的参数');
        options[key] = value;
      }
      probe(options);
    }
  } catch (error) {
    console.error(JSON.stringify({ ok: false, error: error.message }));
    process.exitCode = 1;
  }
}

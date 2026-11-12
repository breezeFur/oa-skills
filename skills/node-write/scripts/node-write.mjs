#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { TextDecoder } from 'node:util';
import { canonical, inspect, validateEvidence, verifyCipher } from './dgs-check.mjs';

const dgsUsage = ' [--dgs-evidence <absolute.txt> --observer <absolute-executable>]';
const usage = 'node node-write.mjs read --target <absolute-path> [--out <absolute.txt>]' + dgsUsage + '\n'
  + 'node node-write.mjs write --target <absolute-path> (--source <absolute.txt> | --stdin) '
  + '(--create | --expect-sha256 <sha256>)' + dgsUsage;
const hash = (bytes) => createHash('sha256').update(bytes).digest('hex');
let written = false;
let writeAttempted = false;
let readAttempted = false;

function utf8(bytes, label) {
  if (bytes.includes(0)) throw new Error(`${label} 包含 NUL 字节，拒绝按文本处理`);
  try {
    return new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(bytes);
  } catch {
    throw new Error(`${label} 不是有效 UTF-8；检查是否仍为密文、原编码不同或内容损坏，不要有损解码`);
  }
}

function absolute(value, label, txt = false) {
  if (!value || !path.isAbsolute(value)) throw new Error(`${label} 必须是绝对路径`);
  const resolved = path.resolve(value);
  if (txt && path.extname(resolved).toLowerCase() !== '.txt') {
    throw new Error(`${label} 必须使用 .txt 暂存文件`);
  }
  return resolved;
}

function options(args) {
  const result = {};
  for (let i = 0; i < args.length; i++) {
    const key = args[i];
    if (!['--target', '--source', '--out', '--expect-sha256', '--create', '--stdin', '--dgs-evidence', '--observer'].includes(key)) {
      throw new Error(`未知参数：${key}`);
    }
    if (Object.hasOwn(result, key)) throw new Error(`重复参数：${key}`);
    if (key === '--create' || key === '--stdin') result[key] = true;
    else {
      const value = args[++i];
      if (!value || value.startsWith('--')) throw new Error(`${key} 缺少值`);
      result[key] = value;
    }
  }
  return result;
}

function run() {
  const [command, ...args] = process.argv.slice(2);
  if (command === '--help' && args.length === 0) {
    console.log(usage);
    return;
  }
  if (!['read', 'write'].includes(command)) throw new Error(usage);
  const opts = options(args);
  const target = absolute(opts['--target'], '目标文件');
  if (Boolean(opts['--dgs-evidence']) !== Boolean(opts['--observer'])) throw new Error('DGS 验证需同时提供 --dgs-evidence 和 --observer');
  const evidence = opts['--dgs-evidence'] ? validateEvidence(opts['--dgs-evidence'], opts['--observer'], target) : null;
  if (command === 'read') {
    if (opts['--source'] || opts['--create'] || opts['--expect-sha256'] || opts['--stdin']) {
      throw new Error('read 只接受 --target、--out 和 DGS 验证参数');
    }
    const before = evidence ? inspect(opts['--observer'], target) : null;
    readAttempted = true;
    const bytes = fs.readFileSync(target);
    const text = utf8(bytes, '目标文件');
    let physical = null;
    if (before && before.sha256 !== hash(bytes)) {
      if (!before.headerHex.toUpperCase().startsWith(evidence.cipherPrefix)) throw new Error('读取前文件头与已验证密文标识不符');
      physical = verifyCipher(opts['--observer'], target, evidence.cipherPrefix, bytes);
    }
    const result = { ok: true, operation: 'read', target, bytes: bytes.length, sha256: hash(bytes), runtime: process.execPath,
      bom: bytes.subarray(0, 3).equals(Buffer.from([0xef, 0xbb, 0xbf])),
      newlines: { crlf: (text.match(/\r\n/g) ?? []).length, lf: (text.match(/(?<!\r)\n/g) ?? []).length,
        cr: (text.match(/\r(?!\n)/g) ?? []).length }, endsWithNewline: /[\r\n]$/.test(text),
      verified: physical ? 'node-readback+independent-cipher' : 'node-readback', ...(physical ? { physical } : {}) };
    if (opts['--out']) {
      const out = absolute(opts['--out'], '暂存文件', true);
      if (canonical(out) === canonical(target)) throw new Error('暂存文件不能与目标文件相同');
      // 新暂存路径避免覆盖另一个任务的草稿。
      fs.writeFileSync(out, bytes, { flag: 'wx' });
      if (!fs.readFileSync(out).equals(bytes)) throw new Error('暂存读回不一致；检查已创建的草稿');
      result.staged = out;
    } else result.text = text;
    console.log(JSON.stringify(result));
    return;
  }
  if (opts['--out']) throw new Error('write 不接受 --out');
  if (Boolean(opts['--source']) === Boolean(opts['--stdin'])) throw new Error('write 必须且只能选择 --source 或 --stdin');
  let bytes;
  if (opts['--stdin']) bytes = fs.readFileSync(0);
  else {
    const source = absolute(opts['--source'], '暂存文件', true);
    if (canonical(source) === canonical(target)
        || (fs.existsSync(target) && canonical(fs.realpathSync(source)) === canonical(fs.realpathSync(target)))) {
      throw new Error('暂存文件不能与目标文件相同');
    }
    bytes = fs.readFileSync(source);
  }
  utf8(bytes, '输入内容');
  const expected = opts['--expect-sha256'];
  if (opts['--create'] ? Boolean(expected) : !expected) {
    throw new Error('write 必须且只能选择 --create 或 --expect-sha256');
  }
  if (expected && !/^[a-f0-9]{64}$/i.test(expected)) throw new Error('SHA-256 必须是 64 位十六进制值');
  if (!opts['--create']) {
    const current = fs.readFileSync(target);
    utf8(current, '目标文件');
    if (hash(current) !== expected.toLowerCase()) throw new Error('目标文件已变化；重新读取并合并修改');
    if (evidence) verifyCipher(opts['--observer'], target, evidence.cipherPrefix, current);
  }
  // 直接写原始路径；DGS 下不用其他后缀的临时文件再 rename。
  writeAttempted = true;
  fs.writeFileSync(target, bytes, { flag: opts['--create'] ? 'wx' : 'w' });
  written = true;
  const actual = fs.readFileSync(target);
  utf8(actual, '写后目标文件');
  if (!actual.equals(bytes)) throw new Error('写后内容与暂存文件不一致；请检查实际文件状态');
  const physical = evidence ? verifyCipher(opts['--observer'], target, evidence.cipherPrefix, actual) : null;
  console.log(JSON.stringify({
    ok: true, operation: 'write', target, bytes: actual.length,
    sha256: hash(actual), verified: evidence ? 'node-readback+independent-cipher' : 'node-readback', runtime: process.execPath,
    ...(physical ? { physical } : {}),
  }));
}

try {
  run();
} catch (error) {
  console.error(JSON.stringify({ ok: false, readAttempted, writeAttempted, written, error: error.message }));
  process.exitCode = 1;
}

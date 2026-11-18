#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { TextDecoder } from 'node:util';
import { canonical, inspect, validateEvidence, verifyCipher } from './dgs-check.mjs';

const dgsUsage = ' [--dgs-evidence <absolute.txt> --observer <absolute-executable>]';
const usage = 'node node-write.mjs read --target <absolute-path> [--out <absolute.txt>]' + dgsUsage + '\n'
  + 'node node-write.mjs write --target <absolute-path> (--source <absolute.txt> | --stdin) '
  + '(--create | --expect-sha256 <sha256> [--allow-format-change])' + dgsUsage;
const hash = (bytes) => createHash('sha256').update(bytes).digest('hex');
const utf8Bom = Buffer.from([0xef, 0xbb, 0xbf]);
let written = false;
let writeAttempted = false;
let readAttempted = false;
let createCleanup;

function utf8(bytes, label) {
  if (bytes.includes(0)) throw new Error(`${label} 包含 NUL 字节，拒绝按文本处理`);
  try {
    return new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(bytes);
  } catch {
    throw new Error(`${label} 不是有效 UTF-8；检查是否仍为密文、原编码不同或内容损坏，不要有损解码`);
  }
}

function format(bytes, text) {
  return {
    bom: bytes.subarray(0, utf8Bom.length).equals(utf8Bom),
    breaks: text.match(/\r\n|\r|\n/g) ?? [],
    endsWithNewline: /[\r\n]$/.test(text),
  };
}

function sameNewlineStyle(before, after) {
  const styles = new Set(before);
  if (styles.size === 0) return new Set(after).size <= 1;
  if (styles.size === 1) return after.every((value) => styles.has(value));
  return before.length === after.length && before.every((value, index) => value === after[index]);
}

function assertSameFormat(before, after) {
  const changes = [];
  if (before.bom !== after.bom) changes.push('UTF-8 BOM');
  if (before.endsWithNewline !== after.endsWithNewline) changes.push('末尾换行');
  if (!sameNewlineStyle(before.breaks, after.breaks)) changes.push('换行类型或混合换行顺序');
  if (changes.length) throw new Error(`输入改变原文件格式（${changes.join('、')}）。请保留原格式；明确需要修改格式时使用 --allow-format-change`);
}

function requireCipherBeforeRead(observer, target, evidence) {
  if (!fs.lstatSync(target).isFile()) throw new Error('DGS 目标必须是位于已验证目录中的普通文件');
  if (!inspect(observer, target).headerHex.startsWith(evidence.cipherPrefix)) {
    throw new Error('读取前独立视角未确认预期密文；请核对目标的 DGS 状态');
  }
}

function sameFile(a, b) {
  return a.isFile() && b.isFile() && a.ino !== 0n && a.dev === b.dev && a.ino === b.ino && a.birthtimeNs === b.birthtimeNs;
}

function removeOwnCreation(target, identity, snapshot) {
  try {
    const current = fs.lstatSync(target, { bigint: true });
    if (!identity || !snapshot || !sameFile(identity, current) || current.size !== snapshot.size
        || current.mtimeNs !== snapshot.mtimeNs || current.ctimeNs !== snapshot.ctimeNs) return 'needs-inspection';
    fs.unlinkSync(target);
    return 'removed';
  } catch (error) {
    return error.code === 'ENOENT' ? 'absent' : 'needs-inspection';
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
    if (!['--target', '--source', '--out', '--expect-sha256', '--create', '--stdin', '--allow-format-change',
      '--dgs-evidence', '--observer'].includes(key)) {
      throw new Error(`未知参数：${key}`);
    }
    if (Object.hasOwn(result, key)) throw new Error(`重复参数：${key}`);
    if (['--create', '--stdin', '--allow-format-change'].includes(key)) result[key] = true;
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
  const observer = opts['--observer'];
  const evidence = observer ? validateEvidence(opts['--dgs-evidence'], observer, target) : null;
  if (command === 'read') {
    if (opts['--source'] || opts['--create'] || opts['--expect-sha256'] || opts['--stdin'] || opts['--allow-format-change']) {
      throw new Error('read 只接受 --target、--out 和 DGS 验证参数');
    }
    if (evidence) requireCipherBeforeRead(observer, target, evidence);
    readAttempted = true;
    const bytes = fs.readFileSync(target);
    const text = utf8(bytes, '目标文件');
    const physical = evidence ? verifyCipher(observer, target, evidence.cipherPrefix, bytes) : null;
    const { bom, breaks, endsWithNewline } = format(bytes, text);
    const newlines = { crlf: 0, lf: 0, cr: 0 };
    for (const value of breaks) newlines[value === '\r\n' ? 'crlf' : value === '\n' ? 'lf' : 'cr']++;
    const result = { ok: true, operation: 'read', target, bytes: bytes.length, sha256: hash(bytes), runtime: process.execPath,
      bom, newlines, endsWithNewline,
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
  if (opts['--create'] && opts['--allow-format-change']) throw new Error('--allow-format-change 仅适用于覆盖');
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
  const text = utf8(bytes, '输入内容');
  const expected = opts['--expect-sha256'];
  if (opts['--create'] ? Boolean(expected) : !expected) {
    throw new Error('write 必须且只能选择 --create 或 --expect-sha256');
  }
  if (expected && !/^[a-f0-9]{64}$/i.test(expected)) throw new Error('SHA-256 必须是 64 位十六进制值');
  if (!opts['--create']) {
    if (evidence) requireCipherBeforeRead(observer, target, evidence);
    readAttempted = true;
    const current = fs.readFileSync(target);
    const currentText = utf8(current, '目标文件');
    if (hash(current) !== expected.toLowerCase()) throw new Error('目标文件已变化；重新读取并合并修改');
    if (!opts['--allow-format-change']) assertSameFormat(format(current, currentText), format(bytes, text));
    if (evidence) verifyCipher(observer, target, evidence.cipherPrefix, current);
  }
  let created = false;
  let identity;
  let snapshot;
  try {
    // Write the original path so DGS can apply its directory and suffix policy.
    writeAttempted = true;
    if (opts['--create']) {
      const fd = fs.openSync(target, 'wx');
      created = true;
      try {
        identity = fs.fstatSync(fd, { bigint: true });
        fs.writeFileSync(fd, bytes);
        written = true;
      } finally {
        fs.closeSync(fd);
        snapshot = fs.lstatSync(target, { bigint: true, throwIfNoEntry: false });
      }
    } else {
      fs.writeFileSync(target, bytes);
      written = true;
    }
    const actual = fs.readFileSync(target);
    if (!actual.equals(bytes)) throw new Error('写后内容与输入不一致；请检查实际文件状态');
    const physical = evidence ? verifyCipher(observer, target, evidence.cipherPrefix, actual) : null;
    console.log(JSON.stringify({
      ok: true, operation: 'write', target, bytes: actual.length,
      sha256: hash(actual), verified: physical ? 'node-readback+independent-cipher' : 'node-readback', runtime: process.execPath,
      ...(physical ? { physical } : {}),
    }));
  } catch (error) {
    if (created) createCleanup = removeOwnCreation(target, identity, snapshot);
    throw error;
  }
}

try {
  run();
} catch (error) {
  console.error(JSON.stringify({ ok: false, readAttempted, writeAttempted, written, createCleanup, error: error.message }));
  process.exitCode = 1;
}

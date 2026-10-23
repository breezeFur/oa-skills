#!/usr/bin/env node
'use strict';

/**
 * edc-report — e-Builder 报表独立 CLI
 * 逻辑源：同仓 Skill 的 ../scripts/（唯一来源）
 */
const { run } = require('./cli');

run(process.argv.slice(2)).catch((err) => {
  console.error(err.message || err);
  process.exit(1);
});

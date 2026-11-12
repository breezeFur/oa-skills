'use strict';
// auth ready only checks state; authentication stays in e10-login.
console.log("登录规则：已有有效会话直接搭建。\n未获取到可用的 E10 会话。本检查不触发登录。Agent 复用用户已提供的真实地址和账号密码，按 weaver-e10-login 发起官方 OAuth；账号密码在官方浏览器登录页使用，不作为 ETEAMSID 参数。缺少匹配 CLI 时自动准备 e10-login@1.5.0。仅在实际验证码、MFA、平台授权或回调不可达时说明具体阻碍；不默认索取 Cookie，不断言所有环境都不能 OAuth。登录完成后再执行一次 auth ready，避免循环检查。\n用户主动提供会话值时才 set；保留快速失败和认证超时，不扫描无关文件。");
process.exit(0);

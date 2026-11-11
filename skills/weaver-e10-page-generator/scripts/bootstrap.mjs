#!/usr/bin/env node

import { spawn } from 'node:child_process'
import {
	closeSync,
	existsSync,
	lstatSync,
	mkdirSync,
	mkdtempSync,
	openSync,
	readdirSync,
	readFileSync,
	realpathSync,
	renameSync,
	statSync,
	unlinkSync,
	writeFileSync,
} from 'node:fs'
import { createRequire } from 'node:module'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const PRODUCT = 'ui-code-agent'
const READY_SCHEMA = 2
const FEATURE_READY_SCHEMA = 1
const RUNTIME_LOCK_SCHEMA = 1
const RUNTIME_ROOT_NAME = 'ui-code-agent-skill-runtime'
const E10_PAGE = 'e10-page'
const UI_CODE_MCP = 'ui-code-mcp'
const EXACT_VERSION = /^\d+\.\d+\.\d+$/
const LOCK_TIMEOUT_MS = 20 * 60_000
const WAIT_INTERVAL_MS = 500
const WAIT_REPORT_INTERVAL_MS = 10_000
// ui-code-mcp is an exact optional peer installed only by the e10-page feature (D415).
const CORE_PACKAGE_NAMES = [
	'@ui-code-agent/validators',
	'@ui-code-agent/ecode-platform',
	'@ui-code-agent/capability-pack',
	'ui-service-mcp',
	'playwright-core',
]
const DOCTOR_CHECKS = {
	core: ['productPackages', 'toolchain', 'uiServiceMcp', 'browserControl'],
	[E10_PAGE]: ['productPackages', 'toolchain', 'uiCodeMcp', 'previewRuntime'],
}

export class BootstrapError extends Error {
	constructor(code, message, stage, logPath) {
		super(`${code}: ${message}`)
		this.name = 'BootstrapError'
		this.code = code
		this.stage = stage
		this.logPath = logPath
	}
}

function json(filename) {
	return JSON.parse(readFileSync(filename, 'utf8'))
}

export function readProduct(
	productFile = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../product.json')
) {
	const product = json(productFile)
	const expected = [
		'nodeEngine',
		'packageName',
		'product',
		'productVersion',
		'registry',
		'schemaVersion',
	]
	if (
		JSON.stringify(Object.keys(product).sort()) !== JSON.stringify(expected) ||
		product.schemaVersion !== 1 ||
		product.product !== PRODUCT ||
		product.packageName !== PRODUCT ||
		!/^\d+\.\d+\.\d+$/.test(product.productVersion) ||
		product.nodeEngine !== '>=22.5'
	) {
		throw new BootstrapError(
			'PRODUCT_MANIFEST_INVALID',
			`${productFile} 不符合 schema 1`,
			'precheck'
		)
	}
	const registry = new URL(product.registry)
	if (!['http:', 'https:'].includes(registry.protocol)) {
		throw new BootstrapError('PRODUCT_MANIFEST_INVALID', 'registry 只允许 http/https', 'precheck')
	}
	return { ...product, registry: registry.href.replace(/\/$/, '') }
}

function plainObject(value) {
	return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function sameKeys(value, keys) {
	return JSON.stringify(Object.keys(value).sort()) === JSON.stringify([...keys].sort())
}

function validateLockfile(lock, label, expectedDependencies, registry) {
	const fail = (message) => {
		throw new BootstrapError('RUNTIME_LOCK_INVALID', `${label}: ${message}`, 'precheck')
	}
	if (
		!plainObject(lock) ||
		lock.lockfileVersion !== 3 ||
		lock.name !== RUNTIME_ROOT_NAME ||
		lock.version !== '0.0.0' ||
		!plainObject(lock.packages)
	) {
		fail('不是受控 lockfile v3')
	}
	const root = lock.packages['']
	if (
		!plainObject(root) ||
		root.name !== RUNTIME_ROOT_NAME ||
		root.version !== '0.0.0' ||
		!plainObject(root.dependencies) ||
		!sameKeys(root.dependencies, Object.keys(expectedDependencies)) ||
		Object.entries(expectedDependencies).some(
			([name, version]) => root.dependencies[name] !== version
		)
	) {
		fail('根依赖与受控 runtime manifest 不一致')
	}
	for (const key of ['devDependencies', 'optionalDependencies', 'peerDependencies']) {
		if (root[key] !== undefined) fail(`根条目不得包含 ${key}`)
	}
	for (const [location, entry] of Object.entries(lock.packages)) {
		if (location === '') continue
		if (
			!location.startsWith('node_modules/') ||
			location.split('/').some((segment) => segment === '..' || segment === '.' || segment === '')
		) {
			fail(`非法包路径 ${location}`)
		}
		if (!plainObject(entry) || typeof entry.version !== 'string' || entry.link === true) {
			fail(`${location} 不是普通 registry 包`)
		}
		if (entry.inBundle === true) continue
		if (
			typeof entry.resolved !== 'string' ||
			!entry.resolved.startsWith(`${registry}/`) ||
			typeof entry.integrity !== 'string' ||
			!entry.integrity.startsWith('sha512-')
		) {
			fail(`${location} 的 resolved/integrity 不在 ${registry}`)
		}
	}
}

export function validateRuntimeLock(value, product) {
	const fail = (message) => {
		throw new BootstrapError('RUNTIME_LOCK_INVALID', message, 'precheck')
	}
	if (
		!plainObject(value) ||
		!sameKeys(value, ['features', 'product', 'productVersion', 'registry', 'schemaVersion']) ||
		value.schemaVersion !== RUNTIME_LOCK_SCHEMA ||
		value.product !== PRODUCT
	) {
		fail('runtime-lock.json 不符合 schema 1')
	}
	const registry = String(value.registry).replace(/\/$/, '')
	if (value.productVersion !== product.productVersion || registry !== product.registry) {
		fail('runtime-lock.json 与 product.json 的版本或 registry 不一致')
	}
	if (!plainObject(value.features) || !sameKeys(value.features, ['core', E10_PAGE])) {
		fail('runtime-lock.json 必须恰好包含 core 与 e10-page')
	}
	const core = value.features.core
	const e10Page = value.features[E10_PAGE]
	const uiCodeMcpVersion = e10Page?.packages?.['']?.dependencies?.[UI_CODE_MCP]
	if (typeof uiCodeMcpVersion !== 'string' || !EXACT_VERSION.test(uiCodeMcpVersion)) {
		fail('e10-page lock 必须精确声明 ui-code-mcp')
	}
	validateLockfile(core, 'core', { [PRODUCT]: product.productVersion }, registry)
	validateLockfile(
		e10Page,
		E10_PAGE,
		{ [PRODUCT]: product.productVersion, [UI_CODE_MCP]: uiCodeMcpVersion },
		registry
	)
	if (core.packages[`node_modules/${UI_CODE_MCP}`]) fail('core lock 不得包含 ui-code-mcp')
	for (const [location, entry] of Object.entries(core.packages)) {
		if (location === '') continue
		const feature = e10Page.packages[location]
		if (
			!feature ||
			feature.version !== entry.version ||
			feature.resolved !== entry.resolved ||
			feature.integrity !== entry.integrity
		) {
			fail(`e10-page lock 未原样包含 core 条目 ${location}`)
		}
	}
	const cli = core.packages[`node_modules/${PRODUCT}`]
	if (
		cli?.version !== product.productVersion ||
		cli.peerDependencies?.[UI_CODE_MCP] !== uiCodeMcpVersion ||
		cli.peerDependenciesMeta?.[UI_CODE_MCP]?.optional !== true
	) {
		fail('core lock 的 CLI 必须以 optional peer 精确声明同一 ui-code-mcp')
	}
	const featureOnly = Object.keys(e10Page.packages).filter(
		(location) => location !== '' && !Object.hasOwn(core.packages, location)
	)
	return {
		core,
		e10Page,
		uiCodeMcpVersion,
		// Only outermost directories: nested node_modules move together with their parent.
		featureOnlyLocations: featureOnly.filter(
			(location) =>
				!featureOnly.some(
					(parent) => parent !== location && location.startsWith(`${parent}/node_modules/`)
				)
		),
	}
}

export function readRuntimeLock(
	product,
	lockFile = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../runtime-lock.json')
) {
	if (!existsSync(lockFile)) return null
	let value
	try {
		value = json(lockFile)
	} catch {
		throw new BootstrapError('RUNTIME_LOCK_INVALID', `${lockFile} 不是 JSON`, 'precheck')
	}
	return validateRuntimeLock(value, product)
}

function environmentValue(env, name, platform = process.platform) {
	if (platform !== 'win32') return env[name]
	return Object.entries(env).find(
		([candidate]) => candidate.toLowerCase() === name.toLowerCase()
	)?.[1]
}

export function productStateRoot({
	platform = process.platform,
	env = process.env,
	homeDirectory = os.homedir(),
} = {}) {
	const api = platform === 'win32' ? path.win32 : path.posix
	const explicitRoot = environmentValue(env, 'UI_CODE_AGENT_HOME', platform)?.trim()
	if (explicitRoot) return api.resolve(explicitRoot)
	if (platform === 'win32') {
		return api.join(
			environmentValue(env, 'LOCALAPPDATA', platform) ??
				api.join(homeDirectory, 'AppData', 'Local'),
			PRODUCT
		)
	}
	if (platform === 'darwin') {
		return api.join(homeDirectory, 'Library', 'Application Support', PRODUCT)
	}
	return api.join(env.XDG_STATE_HOME ?? api.join(homeDirectory, '.local', 'state'), PRODUCT)
}

export function runtimePaths(product, stateRoot = productStateRoot()) {
	const root = path.resolve(stateRoot, 'skill-runtime')
	return {
		root,
		ready: path.join(root, 'ready.json'),
		featureReady: path.join(root, `ready-${E10_PAGE}.json`),
		lock: path.join(root, 'install.lock'),
		releases: path.join(root, 'releases'),
		releaseRoot: path.join(root, 'releases', product.productVersion),
		cache: path.join(root, 'npm-cache'),
		logs: path.join(root, 'logs'),
	}
}

function inside(root, filename) {
	const relative = path.relative(root, filename)
	return (
		relative === '' ||
		(!path.isAbsolute(relative) && relative !== '..' && !relative.startsWith(`..${path.sep}`))
	)
}

function regularFile(filename, root, label) {
	if (!existsSync(filename) || !lstatSync(filename).isFile()) {
		throw new BootstrapError('PACKAGE_ENTRY_INVALID', `${label} 不是普通文件:${filename}`, 'verify')
	}
	const canonical = realpathSync.native(filename)
	if (!inside(realpathSync.native(root), canonical)) {
		throw new BootstrapError(
			'PACKAGE_ENTRY_INVALID',
			`${label} 逃逸 releaseRoot:${canonical}`,
			'verify'
		)
	}
	return canonical
}

function packageEntry(manifest, name, kind) {
	if (kind === 'main') return manifest.main
	if (kind === 'module') {
		if (typeof manifest.exports === 'string') return manifest.exports
		const root = manifest.exports?.['.']
		if (typeof root === 'string') return root
		return root?.import
	}
	if (typeof manifest.bin === 'string') return manifest.bin
	return manifest.bin?.[name]
}

function inspectManifest(manifestPath, releaseRoot, expectedName, expectedVersion, kind = 'none') {
	const manifest = json(manifestPath)
	if (manifest.name !== expectedName || manifest.version !== expectedVersion) {
		throw new BootstrapError(
			'PACKAGE_VERSION_MISMATCH',
			`${expectedName} 期望 ${expectedVersion},实际 ${manifest.name}@${manifest.version}`,
			'verify'
		)
	}
	if (typeof manifest.engines?.node !== 'string' || !manifest.engines.node) {
		throw new BootstrapError(
			'PACKAGE_ENGINE_INVALID',
			`${expectedName} 缺少 engines.node`,
			'verify'
		)
	}
	const packageRoot = realpathSync.native(path.dirname(manifestPath))
	if (!inside(realpathSync.native(releaseRoot), packageRoot)) {
		throw new BootstrapError('PACKAGE_PATH_INVALID', `${expectedName} 不在 releaseRoot`, 'verify')
	}
	const relativeEntry = packageEntry(manifest, expectedName, kind)
	if (kind !== 'none' && (typeof relativeEntry !== 'string' || !relativeEntry)) {
		throw new BootstrapError('PACKAGE_ENTRY_INVALID', `${expectedName} 缺少 ${kind} 入口`, 'verify')
	}
	return {
		name: expectedName,
		version: expectedVersion,
		packageRoot,
		manifestPath: realpathSync.native(manifestPath),
		engines: { node: manifest.engines.node },
		...(relativeEntry
			? {
					entry: regularFile(
						path.resolve(packageRoot, relativeEntry),
						releaseRoot,
						`${expectedName} entry`
					),
				}
			: {}),
	}
}

function resolveDependencyManifest(cliEntry, name) {
	const require = createRequire(cliEntry)
	try {
		return require.resolve(`${name}/package.json`)
	} catch (manifestError) {
		try {
			let cursor = path.dirname(require.resolve(name))
			while (true) {
				const candidate = path.join(cursor, 'package.json')
				if (existsSync(candidate) && json(candidate).name === name) return candidate
				const parent = path.dirname(cursor)
				if (parent === cursor) break
				cursor = parent
			}
		} catch {
			// Report the package-manifest failure below.
		}
		throw new BootstrapError(
			'PACKAGE_MISSING',
			`无法从 ui-code-agent 依赖树解析 ${name}:${manifestError.message}`,
			'verify'
		)
	}
}

function uiCodeMcpPeerVersion(cliManifest) {
	const version = cliManifest.peerDependencies?.[UI_CODE_MCP]
	if (
		typeof version !== 'string' ||
		!EXACT_VERSION.test(version) ||
		cliManifest.peerDependenciesMeta?.[UI_CODE_MCP]?.optional !== true ||
		cliManifest.dependencies?.[UI_CODE_MCP] !== undefined
	) {
		throw new BootstrapError(
			'PACKAGE_DEPENDENCY_NOT_EXACT',
			`${UI_CODE_MCP} 必须是 CLI 的精确 optional peer`,
			'verify'
		)
	}
	return version
}

export function runtimeRootManifest(product, uiCodeMcpVersion) {
	return {
		name: RUNTIME_ROOT_NAME,
		version: '0.0.0',
		private: true,
		dependencies: {
			[PRODUCT]: product.productVersion,
			...(uiCodeMcpVersion ? { [UI_CODE_MCP]: uiCodeMcpVersion } : {}),
		},
	}
}

export function verifyInstalledPackages(releaseRoot, product, { feature = null } = {}) {
	const root = realpathSync.native(releaseRoot)
	const rootManifest = json(path.join(root, 'package.json'))
	if (
		rootManifest.name !== RUNTIME_ROOT_NAME ||
		rootManifest.private !== true ||
		rootManifest.dependencies?.[PRODUCT] !== product.productVersion
	) {
		throw new BootstrapError('RELEASE_ROOT_INVALID', 'release package.json 不受控', 'verify')
	}
	const cliManifestPath = path.join(root, 'node_modules', PRODUCT, 'package.json')
	const cli = inspectManifest(cliManifestPath, root, PRODUCT, product.productVersion, 'bin')
	const cliManifest = json(cliManifestPath)
	for (const name of CORE_PACKAGE_NAMES) {
		const version = cliManifest.dependencies?.[name]
		if (name === 'ui-service-mcp' && version === '*') continue
		if (typeof version !== 'string' || !EXACT_VERSION.test(version)) {
			throw new BootstrapError('PACKAGE_DEPENDENCY_NOT_EXACT', `${name} 不是精确依赖`, 'verify')
		}
	}
	const uiCodeMcpVersion = uiCodeMcpPeerVersion(cliManifest)
	const dependency = (name, kind, version = cliManifest.dependencies[name]) =>
		inspectManifest(resolveDependencyManifest(cli.entry, name), root, name, version, kind)
	const validators = dependency('@ui-code-agent/validators', 'main')
	const ecodePlatform = dependency('@ui-code-agent/ecode-platform', 'main')
	const capabilityPack = dependency('@ui-code-agent/capability-pack', 'none')
	const uiCodeMcp =
		feature === E10_PAGE ? dependency(UI_CODE_MCP, 'bin', uiCodeMcpVersion) : undefined
	const serviceManifestPath = resolveDependencyManifest(cli.entry, 'ui-service-mcp')
	const serviceVersion = json(serviceManifestPath).version
	if (typeof serviceVersion !== 'string' || !EXACT_VERSION.test(serviceVersion)) {
		throw new BootstrapError(
			'PACKAGE_VERSION_MISMATCH',
			'ui-service-mcp 的已安装版本必须是正式版本',
			'verify'
		)
	}
	const uiServiceMcp = inspectManifest(
		serviceManifestPath,
		root,
		'ui-service-mcp',
		cliManifest.dependencies['ui-service-mcp'] === '*'
			? serviceVersion
			: cliManifest.dependencies['ui-service-mcp'],
		'main'
	)
	const playwrightCore = dependency('playwright-core', 'module')
	const protocol = {
		skill: regularFile(
			path.join(capabilityPack.packageRoot, 'SKILL.md'),
			root,
			'protocol SKILL.md'
		),
		agents: regularFile(
			path.join(capabilityPack.packageRoot, 'AGENTS.md'),
			root,
			'protocol AGENTS.md'
		),
		agentsStatic: regularFile(
			path.join(capabilityPack.packageRoot, 'AGENTS-static.md'),
			root,
			'protocol AGENTS-static.md'
		),
	}
	return {
		cli,
		validators,
		ecodePlatform,
		capabilityPack,
		...(uiCodeMcp ? { uiCodeMcp } : {}),
		uiCodeMcpVersion,
		uiServiceMcp,
		playwrightCore,
		protocol,
	}
}

function readyPackageValid(value, expected, releaseRoot, kind) {
	if (!value || value.version !== expected.version || value.packageRoot !== expected.packageRoot) {
		return false
	}
	if (kind && value.entry !== expected.entry) return false
	return inside(releaseRoot, value.packageRoot) && (!kind || inside(releaseRoot, value.entry))
}

export function inspectReady(product = readProduct(), stateRoot = productStateRoot()) {
	const paths = runtimePaths(product, stateRoot)
	if (!existsSync(paths.ready)) return { status: 'missing', reason: 'ready.json missing', paths }
	try {
		const ready = json(paths.ready)
		if (
			ready.schemaVersion !== READY_SCHEMA ||
			ready.product !== PRODUCT ||
			ready.productVersion !== product.productVersion ||
			ready.platform !== process.platform ||
			ready.arch !== process.arch ||
			!['runtime-lock', 'package-spec'].includes(ready.installSource) ||
			ready.doctor?.status !== 'passed' ||
			ready.doctor?.toolchain !== 'passed' ||
			ready.doctor?.browserControl !== 'passed' ||
			ready.doctor?.serviceMcpProtocol !== 'passed'
		) {
			return { status: 'missing', reason: 'ready identity mismatch', paths }
		}
		if (
			!existsSync(paths.releaseRoot) ||
			ready.releaseRoot !== realpathSync.native(paths.releaseRoot)
		) {
			return { status: 'missing', reason: 'releaseRoot mismatch', paths }
		}
		const packages = verifyInstalledPackages(paths.releaseRoot, product)
		if (
			ready.cliEntry !== packages.cli.entry ||
			!readyPackageValid(ready.packages?.uiCodeAgent, packages.cli, ready.releaseRoot, false) ||
			!readyPackageValid(
				ready.packages?.uiServiceMcp,
				packages.uiServiceMcp,
				ready.releaseRoot,
				true
			) ||
			ready.protocol?.skill !== packages.protocol.skill ||
			ready.protocol?.agents !== packages.protocol.agents ||
			ready.protocol?.agentsStatic !== packages.protocol.agentsStatic
		) {
			return { status: 'missing', reason: 'ready package mismatch', paths }
		}
		return { status: 'ready', ready, packages, paths }
	} catch (error) {
		return {
			status: 'missing',
			reason: error instanceof Error ? error.message : String(error),
			paths,
		}
	}
}

export function inspectFeatureReady(product = readProduct(), stateRoot = productStateRoot()) {
	const core = inspectReady(product, stateRoot)
	const paths = core.paths
	if (core.status !== 'ready') return { status: 'missing', reason: `core ${core.reason}`, paths }
	if (!existsSync(paths.featureReady)) {
		return { status: 'missing', reason: `ready-${E10_PAGE}.json missing`, paths, core }
	}
	try {
		const ready = json(paths.featureReady)
		if (
			ready.schemaVersion !== FEATURE_READY_SCHEMA ||
			ready.product !== PRODUCT ||
			ready.feature !== E10_PAGE ||
			ready.productVersion !== product.productVersion ||
			ready.platform !== process.platform ||
			ready.arch !== process.arch ||
			ready.releaseRoot !== core.ready.releaseRoot ||
			ready.coreInstalledAt !== core.ready.installedAt ||
			ready.doctor?.status !== 'passed'
		) {
			return { status: 'missing', reason: 'feature ready identity mismatch', paths, core }
		}
		const packages = verifyInstalledPackages(paths.releaseRoot, product, { feature: E10_PAGE })
		if (
			!readyPackageValid(ready.packages?.uiCodeMcp, packages.uiCodeMcp, ready.releaseRoot, true)
		) {
			return { status: 'missing', reason: 'feature ready package mismatch', paths, core }
		}
		return { status: 'ready', ready, packages, paths, core }
	} catch (error) {
		return {
			status: 'missing',
			reason: error instanceof Error ? error.message : String(error),
			paths,
			core,
		}
	}
}

function parseNode(version) {
	const match = /^v?(\d+)\.(\d+)\.(\d+)/.exec(version)
	return match ? match.slice(1).map(Number) : null
}

export function nodeSupported(version = process.version) {
	const parsed = parseNode(version)
	return Boolean(parsed && (parsed[0] > 22 || (parsed[0] === 22 && parsed[1] >= 5)))
}

const WINDOWS_COMMAND_ENV_PREFIX = 'UI_CODE_AGENT_CMD_VALUE_'
const WORKBUDDY_SESSION_ENV_NAMES = ['CODEBUDDY_SESSION_ID', 'CLAUDE_SESSION_ID']

function npmChildEnvironment(env, cacheDirectory) {
	const childEnv = { ...env }
	for (const name of Object.keys(childEnv)) {
		if (
			WORKBUDDY_SESSION_ENV_NAMES.some(
				(sessionName) => name.toLowerCase() === sessionName.toLowerCase()
			) ||
			['npm_config_cache', 'npm_config_update_notifier'].includes(name.toLowerCase())
		) {
			delete childEnv[name]
		}
	}
	childEnv.npm_config_cache = cacheDirectory
	childEnv.npm_config_update_notifier = 'false'
	return childEnv
}

function windowsCommandEnvironment(command, args, env) {
	const childEnv = { ...env }
	for (const name of Object.keys(childEnv)) {
		if (name.toLowerCase().startsWith(WINDOWS_COMMAND_ENV_PREFIX.toLowerCase())) {
			delete childEnv[name]
		}
	}
	const references = []
	for (const [index, value] of [command, ...args].entries()) {
		const text = String(value)
		if (/[\0\r\n]/.test(text)) {
			throw new BootstrapError(
				'COMMAND_ARGUMENT_INVALID',
				'Windows cmd 参数不得包含 NUL/CR/LF',
				'precheck'
			)
		}
		const name = `${WINDOWS_COMMAND_ENV_PREFIX}${index}`
		childEnv[name] = text.replaceAll('"', '""')
		references.push(`"%${name}%"`)
	}
	return { childEnv, commandLine: `"${references.join(' ')}"` }
}

export function processInvocation(command, args, platform = process.platform, env = process.env) {
	if (/\.(?:mjs|cjs|js)$/i.test(command)) {
		return { command: process.execPath, args: [command, ...args], shell: false }
	}
	if (platform !== 'win32' || !/\.(?:cmd|bat)$/i.test(command)) {
		return { command, args, shell: false }
	}
	const windows = windowsCommandEnvironment(command, args, env)
	return {
		command: environmentValue(env, 'ComSpec', platform)?.trim() || 'cmd.exe',
		args: ['/d', '/s', '/v:off', '/c', windows.commandLine],
		shell: false,
		env: windows.childEnv,
		windowsVerbatimArguments: true,
	}
}

export function resolveNpmPath({
	requested,
	platform = process.platform,
	env = process.env,
	nodePath = process.execPath,
	fileExists = existsSync,
} = {}) {
	const candidates = []
	if (requested) candidates.push(requested)
	const npmExecPath = environmentValue(env, 'npm_execpath', platform)
	if (npmExecPath) candidates.push(npmExecPath)
	const api = platform === 'win32' ? path.win32 : path.posix
	const nodeDirectory = api.dirname(nodePath)
	const npmNames = platform === 'win32' ? ['npm.cmd', 'npm.bat'] : ['npm']
	for (const name of npmNames) candidates.push(api.join(nodeDirectory, name))
	for (const directory of (environmentValue(env, 'PATH', platform) ?? '').split(
		platform === 'win32' ? ';' : ':'
	)) {
		if (directory) for (const name of npmNames) candidates.push(api.join(directory, name))
	}
	const found = candidates.find((candidate) => api.isAbsolute(candidate) && fileExists(candidate))
	if (!found) throw new BootstrapError('NPM_NOT_FOUND', '无法定位绝对 npm 入口', 'precheck')
	return api.resolve(found)
}

export function detectSystemBrowser({
	platform = process.platform,
	env = process.env,
	homeDirectory = os.homedir(),
	fileExists = existsSync,
} = {}) {
	const api = platform === 'win32' ? path.win32 : path.posix
	const explicit = environmentValue(env, 'UI_CODE_AGENT_BROWSER_EXECUTABLE', platform)?.trim()
	if (explicit && api.isAbsolute(explicit) && fileExists(explicit)) return api.resolve(explicit)
	const candidates = []
	if (platform === 'darwin') {
		candidates.push(
			'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
			'/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
			api.join(homeDirectory, 'Applications/Google Chrome.app/Contents/MacOS/Google Chrome'),
			api.join(homeDirectory, 'Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge')
		)
	} else if (platform === 'win32') {
		for (const root of [
			environmentValue(env, 'PROGRAMFILES', platform),
			environmentValue(env, 'PROGRAMFILES(X86)', platform),
			environmentValue(env, 'LOCALAPPDATA', platform),
		].filter(Boolean)) {
			candidates.push(
				api.join(root, 'Google', 'Chrome', 'Application', 'chrome.exe'),
				api.join(root, 'Microsoft', 'Edge', 'Application', 'msedge.exe')
			)
		}
	} else {
		for (const directory of (env.PATH ?? '').split(platform === 'win32' ? ';' : ':')) {
			for (const name of ['google-chrome', 'google-chrome-stable', 'microsoft-edge', 'chromium']) {
				candidates.push(api.join(directory, name))
			}
		}
	}
	return candidates.find((candidate) => fileExists(candidate)) ?? null
}

function redact(value) {
	return String(value)
		.replace(/(_authToken\s*[=:]\s*)[^\s]+/gi, '$1[redacted]')
		.replace(/(npm_[A-Za-z0-9_]*token\s*[=:]\s*)[^\s]+/gi, '$1[redacted]')
}

function runCaptured(command, args, options = {}) {
	return new Promise((resolve, reject) => {
		const invocation = processInvocation(command, args, options.platform, options.env)
		const child = spawn(invocation.command, invocation.args, {
			cwd: options.cwd,
			env: invocation.env ?? options.env,
			shell: invocation.shell,
			windowsVerbatimArguments: invocation.windowsVerbatimArguments,
			stdio: ['ignore', 'pipe', 'pipe'],
		})
		let stdout = ''
		let stderr = ''
		child.stdout.on('data', (chunk) => {
			stdout += String(chunk)
			options.log?.(chunk)
		})
		child.stderr.on('data', (chunk) => {
			stderr += String(chunk)
			options.log?.(chunk)
		})
		child.once('error', reject)
		child.once('close', (code, signal) => resolve({ code: code ?? 1, signal, stdout, stderr }))
	})
}

function processAlive(pid) {
	if (!Number.isSafeInteger(pid) || pid <= 0) return false
	try {
		process.kill(pid, 0)
		return true
	} catch (error) {
		return error?.code !== 'ESRCH'
	}
}

function validLockOwner(value) {
	if (!value || typeof value !== 'object' || Array.isArray(value)) return null
	const keys = Object.keys(value).sort()
	if (JSON.stringify(keys) !== JSON.stringify(['logPath', 'pid', 'productVersion', 'startedAt']))
		return null
	if (
		!Number.isSafeInteger(value.pid) ||
		value.pid <= 0 ||
		typeof value.startedAt !== 'string' ||
		!Number.isFinite(Date.parse(value.startedAt)) ||
		typeof value.productVersion !== 'string' ||
		!/^\d+\.\d+\.\d+$/.test(value.productVersion) ||
		typeof value.logPath !== 'string' ||
		value.logPath.length === 0
	)
		return null
	return value
}

function delay(milliseconds) {
	return new Promise((resolve) => setTimeout(resolve, milliseconds))
}

export async function acquireLock(product, paths, options, logPath) {
	const now = options.now ?? Date.now
	const wait = options.delay ?? delay
	const timeout = options.lockTimeoutMs ?? LOCK_TIMEOUT_MS
	const readyCheck =
		options.readyCheck ?? (() => inspectReady(product, options.stateRoot).status === 'ready')
	const started = now()
	let lastWaitReportAt = Number.NEGATIVE_INFINITY
	for (;;) {
		try {
			const fd = openSync(paths.lock, 'wx', 0o600)
			writeFileSync(
				fd,
				`${JSON.stringify({ pid: process.pid, startedAt: new Date(now()).toISOString(), productVersion: product.productVersion, logPath }, null, 2)}\n`
			)
			closeSync(fd)
			return
		} catch (error) {
			if (error?.code !== 'EEXIST') throw error
		}
		if (readyCheck()) return 'ready'
		let lock = null
		try {
			lock = validLockOwner(json(paths.lock))
		} catch {
			// An invalid lock is only removable after its own bounded age expires.
		}
		let age
		try {
			age = now() - statSync(paths.lock).mtimeMs
		} catch (error) {
			if (error?.code === 'ENOENT') continue
			throw error
		}
		if ((lock && !processAlive(lock.pid)) || (!lock && age > timeout)) {
			try {
				unlinkSync(paths.lock)
			} catch (error) {
				if (error?.code !== 'ENOENT') throw error
			}
			continue
		}
		if (now() - started > timeout * 2) {
			throw new BootstrapError('INSTALL_LOCK_TIMEOUT', '等待另一项初始化超时', 'lock', logPath)
		}
		const currentTime = now()
		if (currentTime - lastWaitReportAt >= WAIT_REPORT_INTERVAL_MS) {
			options.report?.('正在等待另一项初始化完成')
			lastWaitReportAt = currentTime
		}
		await wait(WAIT_INTERVAL_MS)
	}
}

function atomicReady(filename, value) {
	const temporary = `${filename}.${process.pid}.${Date.now()}.tmp`
	writeFileSync(temporary, `${JSON.stringify(value, null, 2)}\n`, { mode: 0o600 })
	renameSync(temporary, filename)
}

function assertNpmTree(value) {
	if (!value || typeof value !== 'object') {
		throw new BootstrapError('NPM_TREE_INVALID', 'npm ls 未返回 JSON 对象', 'verify')
	}
	const problems = []
	const visit = (node, location) => {
		if (!node || typeof node !== 'object') {
			problems.push(`${location}:not-object`)
			return
		}
		for (const problem of Array.isArray(node.problems) ? node.problems : []) {
			problems.push(`${location}:${problem}`)
		}
		for (const flag of ['missing', 'invalid', 'extraneous']) {
			if (node[flag]) problems.push(`${location}:${flag}`)
		}
		for (const [name, dependency] of Object.entries(node.dependencies ?? {})) {
			visit(dependency, `${location}>${name}`)
		}
	}
	visit(value, 'root')
	if (problems.length > 0) {
		throw new BootstrapError('NPM_TREE_INVALID', problems.join('; '), 'verify')
	}
}

function doctorReady(doctor, scope = 'core') {
	return (
		doctor?.ok === true &&
		doctor.scope === scope &&
		DOCTOR_CHECKS[scope].every((name) => doctor[name]?.ok === true)
	)
}

function doctorFailureSummary(doctor, exitCode, scope = 'core') {
	const failures = []
	for (const name of DOCTOR_CHECKS[scope]) {
		const check = doctor?.[name]
		if (check?.ok === true) continue
		const reason = redact(typeof check?.reason === 'string' ? check.reason : '检查未通过').replace(
			/\s+/g,
			' '
		)
		const bounded = reason.length > 320 ? `${reason.slice(0, 160)}…${reason.slice(-160)}` : reason
		failures.push(`${name}: ${bounded}`)
	}
	return (failures.join('; ') || `doctor exit ${exitCode},总自检未通过`).slice(0, 800)
}

function prepareRelease(product, paths, log, report) {
	let staleReady = false
	if (existsSync(paths.ready)) {
		try {
			staleReady = json(paths.ready).productVersion === product.productVersion
		} catch {
			staleReady = true
		}
	}
	try {
		const incomplete = existsSync(paths.releaseRoot) && readdirSync(paths.releaseRoot).length > 0
		if (incomplete || staleReady) {
			const retained = mkdtempSync(
				path.join(paths.releases, `${product.productVersion}.incomplete-`)
			)
			// Retire stale ready first: partial files must not satisfy the old ready during installation.
			if (staleReady) renameSync(paths.ready, path.join(retained, 'ready.json'))
			if (incomplete) renameSync(paths.releaseRoot, path.join(retained, 'release'))
			log(`\n未就绪安装保留位置:${retained}\n`)
			report('检测到未就绪的旧安装，已保留现场，将从空目录重新准备')
		}
		mkdirSync(paths.releaseRoot, { recursive: true })
	} catch (error) {
		throw new BootstrapError(
			'RELEASE_PREPARE_FAILED',
			error instanceof Error ? error.message : String(error),
			'prepare'
		)
	}
}

function writeJsonFile(filename, value) {
	writeFileSync(filename, `${JSON.stringify(value, null, 2)}\n`)
}

function createLog(paths, product, label) {
	const logPath = path.join(
		paths.logs,
		`bootstrap-${label ? `${label}-` : ''}${new Date().toISOString().replace(/[:.]/g, '-')}.log`
	)
	writeFileSync(logPath, `${new Date().toISOString()} ${PRODUCT}@${product.productVersion}\n`, {
		mode: 0o600,
	})
	return { logPath, log: (chunk) => writeFileSync(logPath, redact(chunk), { flag: 'a' }) }
}

function releaseOwnLock(paths) {
	if (!existsSync(paths.lock)) return
	try {
		const lockState = json(paths.lock)
		if (lockState.pid === process.pid) unlinkSync(paths.lock)
	} catch {
		// Never delete an unreadable lock that may belong to another process.
	}
}

function asBootstrapError(error, logPath) {
	if (error instanceof BootstrapError) {
		if (!error.logPath) error.logPath = logPath
		return error
	}
	return new BootstrapError(
		'BOOTSTRAP_FAILED',
		error instanceof Error ? error.message : String(error),
		'unknown',
		logPath
	)
}

function npmFlags(product, paths) {
	return [
		`--registry=${product.registry}`,
		`--@ui-code-agent:registry=${product.registry}`,
		'--cache',
		paths.cache,
		'--ignore-scripts',
	]
}

function npmSpecFlags() {
	return ['--no-save', '--no-package-lock', '--no-audit', '--no-fund', '--engine-strict=false']
}

function npmLockFlags() {
	return ['--no-audit', '--no-fund', '--engine-strict=false']
}

// Local test Skills replace this source of package specs; production uses runtime-lock.json.
function corePackageSpecs(product, options) {
	return [options.packageSpec ?? `${product.packageName}@${product.productVersion}`]
}

async function runNpmInstall(runner, npmPath, args, context) {
	const install = await runner(npmPath, args, {
		cwd: context.releaseRoot,
		env: context.npmEnv,
		log: context.log,
		platform: context.platform,
	})
	if (install.code !== 0) {
		throw new BootstrapError(
			'NPM_INSTALL_FAILED',
			redact(install.stderr || install.stdout || `exit ${install.code}`)
				.trim()
				.slice(-800),
			'install',
			context.logPath
		)
	}
}

async function verifyNpmTree(runner, npmPath, context) {
	const listed = await runner(npmPath, ['ls', '--all', '--json', '--prefix', context.releaseRoot], {
		cwd: context.releaseRoot,
		env: context.npmEnv,
		log: context.log,
		platform: context.platform,
	})
	let npmTree
	try {
		npmTree = JSON.parse(listed.stdout)
	} catch {
		throw new BootstrapError('NPM_TREE_INVALID', 'npm ls 输出不是 JSON', 'verify', context.logPath)
	}
	assertNpmTree(npmTree)
	if (listed.code !== 0) {
		throw new BootstrapError(
			'NPM_TREE_INVALID',
			`npm ls exit ${listed.code}`,
			'verify',
			context.logPath
		)
	}
}

async function runDoctor(runner, cliEntry, scope, context) {
	const args = [cliEntry, 'doctor', '--json', ...(scope === 'core' ? [] : ['--only', scope])]
	const doctorResult = await runner(process.execPath, args, {
		cwd: context.releaseRoot,
		env: context.runtimeEnv,
		log: context.log,
	})
	let doctor
	try {
		doctor = JSON.parse(doctorResult.stdout)
	} catch {
		throw new BootstrapError(
			'DOCTOR_INVALID',
			'doctor 输出不是单一 JSON 文档',
			'doctor',
			context.logPath
		)
	}
	if (doctorResult.code !== 0 || !doctorReady(doctor, scope)) {
		throw new BootstrapError(
			'DOCTOR_FAILED',
			doctorFailureSummary(doctor, doctorResult.code, scope),
			'doctor',
			context.logPath
		)
	}
	return doctor
}

export async function ensureRuntime(options = {}) {
	const product = options.product ?? readProduct(options.productFile)
	const stateRoot = options.stateRoot ?? productStateRoot()
	const current = inspectReady(product, stateRoot)
	if (current.status === 'ready') return current
	const nodeVersion = options.nodeVersion ?? process.version
	if (!nodeSupported(nodeVersion)) {
		throw new BootstrapError(
			'NODE_UNSUPPORTED',
			`需要 Node ${product.nodeEngine},当前 ${nodeVersion}`,
			'precheck'
		)
	}
	const platform = options.platform ?? process.platform
	if (!['darwin', 'win32', 'linux'].includes(platform)) {
		throw new BootstrapError(
			'PLATFORM_UNSUPPORTED',
			`不支持 ${platform}/${process.arch}`,
			'precheck'
		)
	}
	const runtimeEnv = { ...process.env, ...options.env }
	const browser = (options.detectBrowser ?? detectSystemBrowser)({ platform, env: runtimeEnv })
	if (!browser)
		throw new BootstrapError('BROWSER_NOT_FOUND', '未找到系统 Chrome 或 Edge', 'precheck')
	const runtimeLock =
		'runtimeLock' in options
			? options.runtimeLock
			: options.packageSpec === undefined
				? readRuntimeLock(product, options.runtimeLockFile)
				: null
	const paths = runtimePaths(product, stateRoot)
	for (const directory of [paths.root, paths.releases, paths.cache, paths.logs]) {
		mkdirSync(directory, { recursive: true })
	}
	const { logPath, log } = createLog(paths, product)
	const report = options.report ?? ((message) => console.error(message))
	const lock = await acquireLock(product, paths, { ...options, stateRoot, report }, logPath)
	if (lock === 'ready') return inspectReady(product, stateRoot)
	try {
		const repeated = inspectReady(product, stateRoot)
		if (repeated.status === 'ready') return repeated
		report('[1/3] 正在准备本地运行环境')
		const npmPath = resolveNpmPath({
			requested: options.npmPath,
			platform,
			env: runtimeEnv,
			nodePath: options.nodePath ?? process.execPath,
		})
		// Resolve and verify the install source before retiring any previous installation.
		const packageSpecs = runtimeLock ? null : corePackageSpecs(product, options)
		const npmArgs = runtimeLock
			? ['ci', '--prefix', paths.releaseRoot, ...npmFlags(product, paths), ...npmLockFlags()]
			: [
					'install',
					'--prefix',
					paths.releaseRoot,
					...packageSpecs,
					...npmFlags(product, paths),
					...npmSpecFlags(),
				]
		const runner = options.runCaptured ?? runCaptured
		const context = {
			releaseRoot: paths.releaseRoot,
			npmEnv: npmChildEnvironment(runtimeEnv, paths.cache),
			runtimeEnv,
			log,
			logPath,
			platform: options.platform,
		}
		prepareRelease(product, paths, log, report)
		writeJsonFile(path.join(paths.releaseRoot, 'package.json'), runtimeRootManifest(product))
		if (runtimeLock) {
			writeJsonFile(path.join(paths.releaseRoot, 'package-lock.json'), runtimeLock.core)
		}
		await runNpmInstall(runner, npmPath, npmArgs, context)
		report('[2/3] 正在校验页面生成与预览能力')
		const packages = verifyInstalledPackages(paths.releaseRoot, product)
		await verifyNpmTree(runner, npmPath, context)
		await runDoctor(runner, packages.cli.entry, 'core', context)
		const ready = {
			schemaVersion: READY_SCHEMA,
			product: PRODUCT,
			productVersion: product.productVersion,
			platform: process.platform,
			arch: process.arch,
			releaseRoot: realpathSync.native(paths.releaseRoot),
			cliEntry: packages.cli.entry,
			installSource: runtimeLock ? 'runtime-lock' : 'package-spec',
			packages: {
				uiCodeAgent: { version: packages.cli.version, packageRoot: packages.cli.packageRoot },
				uiServiceMcp: {
					version: packages.uiServiceMcp.version,
					packageRoot: packages.uiServiceMcp.packageRoot,
					entry: packages.uiServiceMcp.entry,
				},
			},
			protocol: packages.protocol,
			doctor: {
				status: 'passed',
				toolchain: 'passed',
				browserControl: 'passed',
				serviceMcpProtocol: 'passed',
			},
			installedAt: new Date().toISOString(),
			verifiedAt: new Date().toISOString(),
		}
		atomicReady(paths.ready, ready)
		report('[3/3] 本地环境已就绪,继续当前任务')
		return inspectReady(product, stateRoot)
	} catch (error) {
		throw asBootstrapError(error, logPath)
	} finally {
		releaseOwnLock(paths)
	}
}

function locationPath(root, location) {
	return path.join(root, ...location.split('/'))
}

// A failed feature attempt may leave its packages behind; keep them for diagnosis (D381) and
// reinstall from the npm cache instead of trusting an unverified directory.
function retireIncompleteFeature(product, paths, releaseRoot, featureOnlyLocations, log, report) {
	const present = featureOnlyLocations.filter((location) =>
		existsSync(locationPath(releaseRoot, location))
	)
	const staleReady = existsSync(paths.featureReady)
	if (present.length === 0 && !staleReady) return
	const retained = path.join(
		mkdtempSync(path.join(paths.releases, `${product.productVersion}.incomplete-`)),
		E10_PAGE
	)
	mkdirSync(retained, { recursive: true })
	if (staleReady)
		renameSync(paths.featureReady, path.join(retained, path.basename(paths.featureReady)))
	for (const location of present) {
		const target = locationPath(retained, location)
		mkdirSync(path.dirname(target), { recursive: true })
		renameSync(locationPath(releaseRoot, location), target)
	}
	const hiddenLock = path.join(releaseRoot, 'node_modules', '.package-lock.json')
	if (present.length > 0 && existsSync(hiddenLock)) {
		mkdirSync(path.join(retained, 'node_modules'), { recursive: true })
		renameSync(hiddenLock, path.join(retained, 'node_modules', '.package-lock.json'))
	}
	log(`\n未就绪的 e10-page 安装保留位置:${retained}\n`)
	report('检测到未就绪的公共组件安装，已保留现场，将重新准备')
}

export async function ensureFeature(options = {}) {
	const feature = options.feature ?? E10_PAGE
	if (feature !== E10_PAGE) {
		throw new BootstrapError('ARGUMENT_INVALID', `不支持的 feature:${feature}`, 'ensure')
	}
	const product = options.product ?? readProduct(options.productFile)
	const stateRoot = options.stateRoot ?? productStateRoot()
	const runtimeLock =
		'runtimeLock' in options
			? options.runtimeLock
			: options.packageSpec === undefined
				? readRuntimeLock(product, options.runtimeLockFile)
				: null
	await ensureRuntime({ ...options, product, stateRoot, runtimeLock })
	const current = inspectFeatureReady(product, stateRoot)
	if (current.status === 'ready') return current
	const platform = options.platform ?? process.platform
	const runtimeEnv = { ...process.env, ...options.env }
	const paths = runtimePaths(product, stateRoot)
	const { logPath, log } = createLog(paths, product, E10_PAGE)
	const report = options.report ?? ((message) => console.error(message))
	const readyCheck = () => inspectFeatureReady(product, stateRoot).status === 'ready'
	const lock = await acquireLock(
		product,
		paths,
		{ ...options, stateRoot, report, readyCheck },
		logPath
	)
	if (lock === 'ready') return inspectFeatureReady(product, stateRoot)
	let restoreCore = null
	try {
		const repeated = inspectFeatureReady(product, stateRoot)
		if (repeated.status === 'ready') return repeated
		const core = inspectReady(product, stateRoot)
		if (core.status !== 'ready') {
			throw new BootstrapError('CORE_NOT_READY', `core 未就绪:${core.reason}`, 'precheck')
		}
		const expectedSource = runtimeLock ? 'runtime-lock' : 'package-spec'
		if (core.ready.installSource !== expectedSource) {
			throw new BootstrapError(
				'RUNTIME_LOCK_INVALID',
				`core 安装来源 ${core.ready.installSource} 与当前 Skill 的 ${expectedSource} 不一致`,
				'precheck'
			)
		}
		const uiCodeMcpVersion = core.packages.uiCodeMcpVersion
		if (runtimeLock && runtimeLock.uiCodeMcpVersion !== uiCodeMcpVersion) {
			throw new BootstrapError(
				'RUNTIME_LOCK_INVALID',
				`runtime-lock 的 ui-code-mcp@${runtimeLock.uiCodeMcpVersion} 与 CLI peer ${uiCodeMcpVersion} 不一致`,
				'precheck'
			)
		}
		report('[1/3] 正在准备公共组件运行环境')
		const releaseRoot = core.ready.releaseRoot
		const npmPath = resolveNpmPath({
			requested: options.npmPath,
			platform,
			env: runtimeEnv,
			nodePath: options.nodePath ?? process.execPath,
		})
		retireIncompleteFeature(
			product,
			paths,
			releaseRoot,
			runtimeLock ? runtimeLock.featureOnlyLocations : [`node_modules/${UI_CODE_MCP}`],
			log,
			report
		)
		const manifestFile = path.join(releaseRoot, 'package.json')
		const lockFile = path.join(releaseRoot, 'package-lock.json')
		const coreManifest = readFileSync(manifestFile)
		const coreLock = runtimeLock ? readFileSync(lockFile) : null
		restoreCore = () => {
			writeFileSync(manifestFile, coreManifest)
			if (coreLock) writeFileSync(lockFile, coreLock)
		}
		writeJsonFile(manifestFile, runtimeRootManifest(product, uiCodeMcpVersion))
		if (runtimeLock) writeJsonFile(lockFile, runtimeLock.e10Page)
		const npmArgs = runtimeLock
			? ['install', '--prefix', releaseRoot, ...npmFlags(product, paths), ...npmLockFlags()]
			: [
					'install',
					'--prefix',
					releaseRoot,
					`${UI_CODE_MCP}@${uiCodeMcpVersion}`,
					...npmFlags(product, paths),
					...npmSpecFlags(),
				]
		const runner = options.runCaptured ?? runCaptured
		const context = {
			releaseRoot,
			npmEnv: npmChildEnvironment(runtimeEnv, paths.cache),
			runtimeEnv,
			log,
			logPath,
			platform: options.platform,
		}
		await runNpmInstall(runner, npmPath, npmArgs, context)
		report('[2/3] 正在校验公共组件与预览能力')
		const packages = verifyInstalledPackages(releaseRoot, product, { feature: E10_PAGE })
		await verifyNpmTree(runner, npmPath, context)
		const doctor = await runDoctor(runner, packages.cli.entry, E10_PAGE, context)
		const uiIdentity = doctor.uiCodeMcp.identity
		atomicReady(paths.featureReady, {
			schemaVersion: FEATURE_READY_SCHEMA,
			product: PRODUCT,
			feature: E10_PAGE,
			productVersion: product.productVersion,
			platform: process.platform,
			arch: process.arch,
			releaseRoot,
			coreInstalledAt: core.ready.installedAt,
			packages: {
				uiCodeMcp: {
					version: packages.uiCodeMcp.version,
					packageRoot: packages.uiCodeMcp.packageRoot,
					entry: packages.uiCodeMcp.entry,
				},
			},
			doctor: {
				status: 'passed',
				uiMcpIdentity: `${uiIdentity.serverName}@${uiIdentity.serverVersion}/schema-${uiIdentity.responseSchemaVersion}:${uiIdentity.library.id}#${uiIdentity.library.dataChecksum}`,
				previewRuntimeChecksum: doctor.previewRuntime.runtimeChecksum,
			},
			installedAt: new Date().toISOString(),
			verifiedAt: new Date().toISOString(),
		})
		restoreCore = null
		report('[3/3] 公共组件运行环境已就绪,继续当前任务')
		return inspectFeatureReady(product, stateRoot)
	} catch (error) {
		if (restoreCore) {
			try {
				restoreCore()
				log('\n已恢复 core 根 manifest/lock\n')
			} catch (restoreError) {
				log(`\n恢复 core 根 manifest/lock 失败:${String(restoreError)}\n`)
			}
		}
		throw asBootstrapError(error, logPath)
	} finally {
		releaseOwnLock(paths)
	}
}

function argumentValue(args, name) {
	for (const [index, value] of args.entries()) {
		if (value === name) return args[index + 1]
		if (typeof value === 'string' && value.startsWith(`${name}=`))
			return value.slice(name.length + 1)
	}
	return undefined
}

function projectKind(projectDir) {
	const marker = path.join(projectDir, '.ui-code-agent', 'project.json')
	if (existsSync(marker)) {
		try {
			const kind = json(marker).kind
			if (kind === E10_PAGE || kind === 'static-html') return kind
		} catch {
			// Mirrors the CLI: a malformed marker falls back to the project skeleton.
		}
	}
	return existsSync(path.join(projectDir, 'build.json')) ? E10_PAGE : null
}

/** Returns the runtime feature a CLI invocation needs before it may start. */
export function requiredFeature(args, cwd = process.cwd()) {
	if (argumentValue(args, '--kind') === E10_PAGE) return E10_PAGE
	if (['components', 'icons'].includes(args[0])) return E10_PAGE
	const dir = argumentValue(args, '--dir')
	if (typeof dir === 'string' && dir && projectKind(path.resolve(cwd, dir)) === E10_PAGE) {
		return E10_PAGE
	}
	return null
}

function bootstrapEntry() {
	return fileURLToPath(import.meta.url)
}

export function e10PageRuntimeGuidance(bootstrapPath = bootstrapEntry()) {
	return {
		fix: `当前任务使用 React + 公共组件体系，本机尚未准备组件运行环境。先向用户发送一次：“使用公共组件体系需要在本机准备组件运行环境，预计需要几分钟，准备完成后继续当前任务。”再以 Bash tool timeout=600000 ms 直接执行 node "${bootstrapPath}" ensure --feature e10-page --json；禁止附加管道或包装脚本，只有退出码为 0 才继续。`,
		next: '准备成功后重新执行刚才的原命令；失败时向用户报告失败阶段、原因和日志路径并结束当前回合。',
	}
}

export function processTreeTerminationInvocation(pid, platform = process.platform) {
	if (platform !== 'win32' || !Number.isSafeInteger(pid) || pid <= 0) return null
	return { command: 'taskkill.exe', args: ['/pid', String(pid), '/t', '/f'], shell: false }
}

function spawnCli(cliEntry, args, env = process.env) {
	return new Promise((resolve, reject) => {
		const child = spawn(process.execPath, [cliEntry, ...args], {
			stdio: 'inherit',
			env,
		})
		const handlers = new Map()
		let forwardedSignal = null
		for (const signal of ['SIGINT', 'SIGTERM']) {
			const handler = () => {
				if (forwardedSignal || child.exitCode !== null || child.signalCode !== null) return
				forwardedSignal = signal
				const termination = processTreeTerminationInvocation(child.pid)
				if (!termination) {
					child.kill(signal)
					return
				}
				const killer = spawn(termination.command, termination.args, {
					stdio: 'ignore',
					windowsHide: true,
				})
				killer.once('error', () => child.kill('SIGKILL'))
				killer.once('close', (code) => {
					if (code !== 0 && child.exitCode === null && child.signalCode === null) {
						child.kill('SIGKILL')
					}
				})
			}
			handlers.set(signal, handler)
			process.once(signal, handler)
		}
		child.once('error', reject)
		child.once('close', (code, signal) => {
			for (const [name, handler] of handlers) process.removeListener(name, handler)
			resolve({
				code:
					forwardedSignal === 'SIGINT'
						? 130
						: forwardedSignal === 'SIGTERM'
							? 143
							: (code ?? (signal ? 1 : 0)),
				signal: forwardedSignal ?? signal,
			})
		})
	})
}

function publicStatus(status, feature) {
	const features = { [E10_PAGE]: feature?.status === 'ready' ? 'ready' : 'missing' }
	return status.status === 'ready'
		? {
				status: 'ready',
				product: PRODUCT,
				productVersion: status.ready.productVersion,
				verifiedAt: status.ready.verifiedAt,
				features,
			}
		: { status: 'missing', product: PRODUCT, reason: status.reason, features }
}

function ensureArguments(args) {
	let json = false
	let feature = null
	for (let index = 0; index < args.length; index += 1) {
		const value = args[index]
		if (value === '--json' && !json) json = true
		else if (value === '--feature' && feature === null && args[index + 1] === E10_PAGE) {
			feature = E10_PAGE
			index += 1
		} else if (value === `--feature=${E10_PAGE}` && feature === null) feature = E10_PAGE
		else {
			throw new BootstrapError(
				'ARGUMENT_INVALID',
				'ensure 只接受 --json 与 --feature e10-page',
				'ensure'
			)
		}
	}
	return { json, feature }
}

export async function main(argv = process.argv.slice(2)) {
	const [command, ...args] = argv
	const product = readProduct()
	if (command === 'status') {
		if (args.length > 1 || (args.length === 1 && args[0] !== '--json')) {
			throw new BootstrapError('ARGUMENT_INVALID', 'status 只接受 --json', 'status')
		}
		console.log(
			JSON.stringify(publicStatus(inspectReady(product), inspectFeatureReady(product)), null, 2)
		)
		return 0
	}
	if (command === 'ensure') {
		const { feature } = ensureArguments(args)
		if (feature) {
			const ready = await ensureFeature({ product, feature })
			console.log(JSON.stringify(publicStatus(ready.core, ready), null, 2))
			return 0
		}
		const ready = await ensureRuntime({ product })
		console.log(JSON.stringify(publicStatus(ready, inspectFeatureReady(product)), null, 2))
		return 0
	}
	if (command === 'protocol') {
		if (args.length > 1 || (args.length === 1 && args[0] !== '--json')) {
			throw new BootstrapError('ARGUMENT_INVALID', 'protocol 只接受 --json', 'protocol')
		}
		const ready = await ensureRuntime({ product })
		console.log(
			JSON.stringify(
				{
					status: 'ready',
					productVersion: product.productVersion,
					skill: ready.packages.protocol.skill,
					agents: ready.packages.protocol.agents,
					agentsStatic: ready.packages.protocol.agentsStatic,
				},
				null,
				2
			)
		)
		return 0
	}
	if (command === 'run') {
		if (args[0] !== '--' || args.length === 1) {
			throw new BootstrapError('ARGUMENT_INVALID', '用法: bootstrap.mjs run -- <CLI 参数>', 'run')
		}
		const cliArgs = args.slice(1)
		const ready = await ensureRuntime({ product })
		const feature = requiredFeature(cliArgs)
		if (feature && inspectFeatureReady(product).status !== 'ready') {
			throw new BootstrapError(
				'E10_PAGE_RUNTIME_NOT_READY',
				'当前命令需要 React + 公共组件体系运行环境，本机尚未准备',
				'run'
			)
		}
		const result = await spawnCli(ready.ready.cliEntry, cliArgs, {
			...process.env,
			UI_CODE_AGENT_BOOTSTRAP: bootstrapEntry(),
		})
		return result.code
	}
	throw new BootstrapError('ARGUMENT_INVALID', '命令必须是 status|ensure|protocol|run', 'arguments')
}

if (process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url) {
	try {
		process.exitCode = await main()
	} catch (error) {
		const value =
			error instanceof BootstrapError
				? error
				: new BootstrapError('BOOTSTRAP_FAILED', String(error))
		if (value.code === 'E10_PAGE_RUNTIME_NOT_READY') {
			const guidance = e10PageRuntimeGuidance()
			console.error(`错误: ${value.message}`)
			console.error(`FIX: ${guidance.fix}`)
			console.error(`NEXT: ${guidance.next}`)
			process.exitCode = 1
		} else {
			console.error(`初始化失败阶段:${value.stage ?? 'unknown'}`)
			console.error(`原因:${value.message}`)
			if (value.logPath) console.error(`日志:${path.resolve(value.logPath)}`)
			console.error(
				'请报告此失败摘要与日志；不要自行 npm 安装、补写依赖文件或删除运行目录。后续重新发起任务时，由同一 Skill 的 ensure 从空目录恢复。'
			)
			process.exitCode = 1
		}
	}
}

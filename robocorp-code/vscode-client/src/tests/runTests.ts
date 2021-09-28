// import * as path from 'path';
//
// import { runTests } from 'vscode-test';
//
// async function main() {
// 	try {
// 		// The folder containing the Extension Manifest package.json
// 		// Passed to `--extensionDevelopmentPath`
//
// 		const extensionDevelopmentPath = path.resolve(__dirname, '../../');
//
// 		// The path to the extension test script
// 		// Passed to --extensionTestsPath
// 		const extensionTestsPath = path.resolve(__dirname, './suite/index');
//
// 		// Download VS Code, unzip it and run the integration test
// 		await runTests({
// 			'extensionPath': extensionDevelopmentPath,
// 			'testRunnerPath': extensionTestsPath,
// 			// Note: __dirname is the directory in 'out', so, base it on the extensionDevelopmentPath to use 'src'.
// 			'testWorkspace': path.resolve(extensionDevelopmentPath, './src/tests/resources')
// 		});
// 	} catch (err) {
// 		console.error('Failed to run tests');
// 		process.exit(1);
// 	}
// }
//
// main();

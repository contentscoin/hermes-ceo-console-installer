const { notarize } = require('@electron/notarize');

exports.default = async function notarizing(context) {
  const { electronPlatformName, appOutDir } = context;
  if (electronPlatformName !== 'darwin') return;

  const appName = context.packager.appInfo.productFilename;
  // Use HERMES_NOTARIZE_* names intentionally. electron-builder also watches
  // APPLE_ID-style env vars and can trigger its built-in notarization path before
  // this afterSign hook, which is brittle for this package version.
  const appleId = process.env.HERMES_NOTARIZE_APPLE_ID;
  const appleIdPassword = process.env.HERMES_NOTARIZE_APPLE_APP_SPECIFIC_PASSWORD;
  const teamId = process.env.HERMES_NOTARIZE_APPLE_TEAM_ID;

  if (!appleId || !appleIdPassword || !teamId) {
    console.log('Skipping macOS notarization: HERMES_NOTARIZE_APPLE_ID / HERMES_NOTARIZE_APPLE_APP_SPECIFIC_PASSWORD / HERMES_NOTARIZE_APPLE_TEAM_ID not fully set.');
    return;
  }

  console.log(`Notarizing ${appName}.app with Apple Team ${teamId}...`);
  return await notarize({
    appBundleId: 'com.fmg.hermes-ceo-console',
    appPath: `${appOutDir}/${appName}.app`,
    appleId,
    appleIdPassword,
    teamId,
  });
};

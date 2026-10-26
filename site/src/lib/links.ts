export const REPO_LABEL = 'github.com/schrodlm/rentczecher';
export const REPO_URL = `https://${REPO_LABEL}`;
export const ISSUES_URL = `${REPO_URL}/issues`;
export const NEW_ISSUE_URL = `${REPO_URL}/issues/new`;
export const RELEASES_URL = `${REPO_URL}/releases`;
// The release workflow publishes every installer under these names, without
// the version, so the latest release always answers them.
const LATEST_DOWNLOAD_URL = `${RELEASES_URL}/latest/download`;
export const WINDOWS_INSTALLER_URL = `${LATEST_DOWNLOAD_URL}/rentczecher-windows-x64-setup.exe`;
export const MACOS_INSTALLER_URL = `${LATEST_DOWNLOAD_URL}/rentczecher-macos-arm64.dmg`;
export const LINUX_APPIMAGE_URL = `${LATEST_DOWNLOAD_URL}/rentczecher-linux-x86_64.AppImage`;
export const LINUX_DEB_URL = `${LATEST_DOWNLOAD_URL}/rentczecher-linux-amd64.deb`;
export const CLONE_COMMAND = `git clone ${REPO_URL}.git`;

export const SUPPORT_URL = 'https://github.com/sponsors/schrodlm';

export const CONTACT_EMAIL = 'matej.schrodl@gmail.com';

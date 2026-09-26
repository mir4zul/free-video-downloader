const MENU_ID = "free-video-downloader-send-video";
const APP_SCHEME = "free-video-downloader://download?url=";

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({
      id: MENU_ID,
      title: "Download video with Free Video Downloader",
      contexts: ["video"]
    });
  });
});

function isHttpUrl(value) {
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

function isYoutubePage(value) {
  try {
    const host = new URL(value).hostname.toLowerCase();
    return host === "youtu.be" || host.endsWith(".youtube.com") ||
      host === "youtube.com" || host.endsWith(".youtube-nocookie.com");
  } catch {
    return false;
  }
}

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId !== MENU_ID) return;

  const pageUrl = info.pageUrl || tab?.url || "";
  // YouTube's media element often exposes an expiring/blob stream URL. yt-dlp
  // needs the watch page URL to inspect the available formats instead.
  const targetUrl = isYoutubePage(pageUrl)
    ? pageUrl
    : (isHttpUrl(info.srcUrl) ? info.srcUrl : pageUrl);

  if (!isHttpUrl(targetUrl)) return;
  chrome.tabs.create({ url: APP_SCHEME + encodeURIComponent(targetUrl) });
});

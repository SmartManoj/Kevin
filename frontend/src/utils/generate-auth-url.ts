/**
 * Generates a URL to redirect to for OAuth authentication
 * @param identityProvider The identity provider to use (e.g., "github", "gitlab")
 * @param requestUrl The URL of the request
 * @returns The URL to redirect to for OAuth
 */
export const generateGitHubAuthUrl = (clientId: string, requestUrl: URL) => {
  const redirectUri = `${requestUrl.origin}/api/user/callback`;
  const scope = "repo,user,workflow,offline_access";
  return `https://github.com/login/oauth/authorize?client_id=${clientId}&redirect_uri=${encodeURIComponent(redirectUri)}&scope=${encodeURIComponent(scope)}`;
};

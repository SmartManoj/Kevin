import { I18nKey } from "#/i18n/declaration";

const KEY_1 = I18nKey.SUGGESTIONS$HACKER_NEWS;
const VALUE_1 = `Please write a python script which displays the top story on Hacker News using v0 api. It should show the title, the link, and the number of points.`;

const KEY_2 = `Fetch Trending Github Repositories`;
const VALUE_2 = `Fetch and Display the Latest Top 5 Trending Repositories on GitHub.`;

const KEY_3 = `Print Bitcoin Price in INR`;
const VALUE_3 = `Print Bitcoin Price in INR`;

export const NON_REPO_SUGGESTIONS: Record<string, string> = {
  [KEY_1]: VALUE_1,
  [KEY_2]: VALUE_2,
  [KEY_3]: VALUE_3,
};

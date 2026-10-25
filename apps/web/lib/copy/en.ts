/** UI strings (English, v1). One catalogue so later i18n is a swap, not a rewrite. */
export const copy = {
  appName: "[App name]",
  appDescription: "Turn the people you already know into the outcome you want.",
  nav: {
    label: "Main",
    today: "Today",
    people: "People",
    capture: "Capture by voice",
    progress: "Progress",
    replies: "Replies",
    repliesBadge: (count: number) => `${count} waiting for a reply check`,
  },
  pages: {
    today: { title: "Today", empty: "Your people for today will show up here." },
    people: { title: "People", empty: "The people you bring in will show up here." },
    capture: { title: "Capture", empty: "Voice and text capture arrives in Sprint 5." },
    progress: { title: "Progress", empty: "Your goal progress will show up here." },
    replies: { title: "Did they reply?", empty: "People you message will show up here." },
    settings: { title: "Settings", empty: "Profile and privacy settings arrive in Sprint 1." },
  },
  status: {
    title: "System status",
    checking: "Checking the API…",
    unreachable: "Can't reach the API. Is `make dev` running?",
    api: "API",
    db: "Database",
    redis: "Redis",
    ok: "ok",
    down: "down",
  },
  offline: {
    title: "You're offline",
    body: "Check your connection, then try again. Nothing you've sent is affected.",
    retry: "Try again",
  },
  common: {
    loading: "Loading",
    settings: "Settings",
  },
} as const;

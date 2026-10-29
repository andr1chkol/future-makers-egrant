# Shared UI conventions

The workspace uses a quiet document-desk layout: warm paper, dark green text,
plain navigation and Georgia headings. Body text uses locally available Trebuchet
MS with a sans-serif fallback. Startup makes no font/CDN request. Keep these
shared tokens and controls when adding feature pages.

## Components and interaction

Use `shared/ui.tsx` for Button, Notice and unavailable feature states. Pages
export through their feature's `index.ts` and require no props. Route parameters
and the generated client supply data. Keep product labels in Slovak.

Navigation uses Lucide outline icons beside visible labels. Decorative icons
are hidden from assistive technology. Active navigation has a border and weight
change as well as background color. All controls have visible keyboard focus;
a first-tab skip link focuses main content. Interactive areas are at least
44 CSS pixels high. Hover and press feedback do not move the layout. Transitions
are disabled under prefers-reduced-motion. Login errors stay inline, describe
the field and restore focus after rejected credentials. Password-manager entry
and paste remain available.

Fixture mode has a persistent yellow banner after session discovery. Provider
state is explicit; no demonstration is labeled as live. Unimplemented pages
explain that they are unavailable without providing a fake upload/confirm action.

## Contrast and layout checks

Measured WCAG contrast ratios for CSS color pairs:

| Pair | Ratio |
|---|---:|
| Body on paper | 11.28:1 |
| Secondary on paper | 5.16:1 |
| Button text on green | 7.53:1 |
| Fixture text on yellow | 8.28:1 |
| Error text on paper | 7.01:1 |
| Notice text on surface | 10.31:1 |

The browser suite covers the fixture banner, navigation, skip link, failed login,
reduced-motion media and text scaling at 375, 768, 1024 and 1440 CSS pixels. It
checks horizontal overflow and captures desktop/mobile screenshots as local/CI
artifacts. These are shell checks, not a screen-reader audit or full domain UX test.
Dark mode is not implemented; do not claim dark-theme verification.

## UI UX Pro Max application

The requested `ui-ux-pro-max` skill was read from
[nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)
at commit `28b3b8dee8c976df4fa3e94aed4e092ad43fcb03`. Its keyboard-navigation,
focus-state and inline-error database matches informed the accessibility pass;
React guidance confirmed surfaced async errors and accessible testing queries.
The two design-system composition searches returned a marketplace and an
operations landing page, which do not fit this document-review workspace. Those
compositions were not adopted or persisted. Existing visual choices remain;
accessibility guidance comes from the matched rules and skill priority defaults.
The skill source stays in the ignored local tools directory, outside app runtime.

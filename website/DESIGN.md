# Dotfiles documentation

This site documents my dotfiles and helps readers install, understand, and use the checkout. Use first-person language for personal descriptions, such as “My dotfiles,” rather than referring to me in the third person. Installation, configuration composition, and terminal copying must be easy to find. README.md and docs/ own all Markdown and MDX content. Every website page is generated from those shared sources; website/ contains presentation and build tooling only.

The established visual identity is the Nord terminal/mountain mark in `../docs/brand/README.md`. Preserve that image and its transparency. Match my personal website, lanej.io. Its `STYLE.md` and `assets/css/site.css` at revision `7c90d7406cfb111b8be0fdbfb8c9009468c1bad3` own the reference: deep green background, pale sage accents, system sans-serif, modest heading weights, and thin rules. `src/styles/custom.css` adapts those tokens to Starlight’s navigation, search, and components. The personal site is dark-only; the light palette is a documentation-specific adaptation, with the existing system preference and theme switcher retained. The Nord project logo keeps its original colors. Revised screenshots remain subject to review.

Prefer readable, bounded prose and direct navigation over decoration. The landing page offers four meaningful destinations and a compact installation overview. Reference pages retain technical detail and horizontally scrollable tables/code. A long reference document is intentional; a duplicated manual is not.

### DOCS-001

Mandatory: readers can search for Zellij copying and reach the canonical session-buffer distinction. The Playwright workflow checks this through the production search index. Empty and loading search states remain Starlight/Pagefind’s responsibility and are inspected manually. A source edit requires regeneration before it appears in the site.

### DOCS-002

Mandatory: the home and terminal guide remain readable on desktop and mobile. Viewrule checks visible main-content text at 14px or above and clipping of prose. Visual review assesses hierarchy, logo rendering, contrast, and intentional table scrolling; geometry alone cannot establish quality. Built-in navigation collapses on mobile, preserving a usable menu. Keyboard focus, skip navigation, search dismissal, and theme persistence are inspected in the rendered application.

### DOCS-003

Mandatory: reference links reach their original source or a generated local destination. The source synchronizer owns link translation and edit destinations. A build and local link crawl assess generated routes and anchors; upstream availability is separate. The site is static with no user data, forms, or server mutations. Search errors can be recovered by dismissing the dialog and using navigation.

Hosting and the final URL are unresolved and outside this change. No deployment workflow is included. The older setup-requirements document conflicts with the current default Make target; the architecture guide identifies this existing discrepancy instead of changing installer behavior.

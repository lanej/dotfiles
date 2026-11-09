const groups = [
  { label: 'Navigation', items: [
    ['Smart pane navigation', 'smart-navigation'],
    ['Status bar and tab titles', 'status-bar'],
    ['Tab picker', 'tab-picker'],
    ['Session picker', 'session-picker'],
    ['Swap tabs', 'tab-swap'],
  ] },
  { label: 'Pane arrangement', items: [
    ['Move a pane', 'move-pane'],
    ['Gather panes', 'gather-panes'],
    ['Equalize panes', 'equalize'],
    ['Golden-ratio sizing', 'golden-ratio'],
  ] },
  { label: 'Sessions', items: [
    ['Shared popup', 'shared-popup'],
    ['Command prompt', 'command-prompt'],
    ['Create and rename sessions', 'sessions'],
    ['Detach one client', 'detach-client'],
    ['Shut down a session', 'shutdown'],
    ['SSH and forwarded agents', 'ssh-agent'],
  ] },
  { label: 'Text and attention', items: [
    ['Copy and paste', 'copy-paste'],
    ['Attention and triage', 'attention'],
    ['Notifications and history', 'notifications'],
  ] },
];

export const zellijPages = groups.flatMap((group) => group.items.map(([, name]) => ({
  file: `docs/zellij/${name}.mdx`, slug: `reference/zellij/${name}`,
})));

export const zellijSidebar = groups.map((group) => ({
  label: group.label,
  collapsed: true,
  items: group.items.map(([label, name]) => ({ label, slug: `reference/zellij/${name}` })),
}));

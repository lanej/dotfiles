import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import { site, base } from './site.config.mjs';
import { zellijSidebar } from './zellij.config.mjs';
import { visit } from 'unist-util-visit';
export default defineConfig({
  site,
  base,
  integrations: [starlight({
    title: 'Dotfiles',
    components: { SiteTitle: './src/components/SiteTitle.astro' },
    favicon: '/source/docs/brand/dotfiles-logo.png',
    description: "My working environment. Configuration, tools, and terminal workflows for macOS and Linux.",
    logo: { src: '../docs/brand/dotfiles-logo.png' },
    social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/lanej/dotfiles' }],
    expressiveCode: {
      shiki: { langAlias: { tmux: 'shellscript' } },
      plugins: [{
        name: 'keyboard-scrollable-code',
        hooks: {
          postprocessRenderedBlock({ renderData }) {
            // WHY: Overflowing command examples must be scrollable without a mouse.
            visit(renderData.blockAst, 'element', (node) => {
              if (node.tagName === 'pre') node.properties.tabIndex = 0;
            });
          },
        },
      }],
    },
    customCss: ['./src/styles/custom.css'],
    sidebar: [
      { label: 'Start here', items: [
        { label: 'Overview', slug: '' },
        { label: 'Install & set up', slug: 'reference/install' },
        { label: 'Configuration composition', slug: 'reference/configuration' },
        { label: 'Architecture', slug: 'architecture' },
        { label: 'Tech radar', slug: 'reference/radar' },
      ] },
      { label: 'Daily workflows', items: [
        { label: 'Terminal & copying', slug: 'terminal' },
        { label: 'Mac approval over SSH', slug: 'reference/keylease-ssh' },
        { label: 'tmux sessions', slug: 'reference/tmux' },
        { label: 'Worktrees', items: [
          { label: 'Treehouse agent worktrees', slug: 'reference/treehouse' },
          { label: 'Tracking and budgets', slug: 'reference/worktree-policy' },
          { label: 'Patched Git installation', slug: 'reference/worktree-hooks' },
        ] },
      ] },
      { label: 'Zellij', items: [
        { label: 'Overview', slug: 'reference/zellij' },
        { label: 'Keybinding map', slug: 'reference/zellij-keybinds' },
        ...zellijSidebar,
      ] },
      { label: 'Reference', items: [
        { label: 'Design system', items: [
          { label: 'Tokens and components', slug: 'design-system' },
          { label: 'Presets', items: [{ label: 'Nord preset', slug: 'design-system/nord' }] },
        ] },
        { label: 'Components', slug: 'components' },
        { label: 'Builder', slug: 'reference/builder' },
        { label: 'macOS stack', slug: 'reference/macos' },
        { label: 'Linux stack', slug: 'reference/linux' },
        { label: 'Rust', slug: 'reference/rust' },
        { label: 'Go style guide', slug: 'reference/go-style' },
        { label: 'TypeScript style guide', slug: 'reference/typescript-style' },
        { label: 'Repository bootstrap', slug: 'reference/repository-bootstrap' },
      ] },
      { label: 'Contributing', items: [
        { label: 'Code comments', slug: 'contributing/code-comments' },
        { label: 'Pull requests', slug: 'contributing/pull-requests' },
        { label: 'Maintain this site', slug: 'maintaining' },
      ] },
    ],
  })],
});

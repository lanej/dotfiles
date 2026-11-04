import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
export default defineConfig({
  integrations: [starlight({
    title: 'Dotfiles',
    description: "Josh Lane’s working environment. Configuration, tools, and terminal workflows for macOS and Linux.",
    logo: { src: '../docs/brand/dotfiles-logo.png' },
    social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/lanej/dotfiles' }],
    expressiveCode: { shiki: { langAlias: { tmux: 'shellscript' } } },
    customCss: ['./src/styles/custom.css'],
    editLink: { baseUrl: 'https://github.com/lanej/dotfiles/edit/master/website/' },
    sidebar: [
      { label: 'Start here', items: [
        { label: 'Overview', slug: '' },
        { label: 'Install & set up', slug: 'reference/install' },
        { label: 'Configuration composition', slug: 'reference/configuration' },
        { label: 'Architecture', slug: 'architecture' },
      ] },
      { label: 'Daily workflows', items: [
        { label: 'Terminal & copying', slug: 'terminal' },
        { label: 'Zellij', slug: 'reference/zellij' },
        { label: 'tmux sessions', slug: 'reference/tmux' },
      ] },
      { label: 'Reference', items: [
        { label: 'Components', slug: 'components' },
        { label: 'macOS stack', slug: 'reference/macos' },
        { label: 'Linux stack', slug: 'reference/linux' },
        { label: 'Rust', slug: 'reference/rust' },
        { label: 'Repository bootstrap', slug: 'reference/repository-bootstrap' },
      ] },
      { label: 'Contributing', items: [{ label: 'Maintain this site', slug: 'maintaining' }] },
    ],
  })],
});

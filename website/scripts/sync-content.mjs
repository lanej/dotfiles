import { readFile, writeFile, mkdir, cp, rm } from 'node:fs/promises';
import { dirname, resolve, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { unified } from 'unified';
import remarkParse from 'remark-parse';
import remarkGfm from 'remark-gfm';
import remarkMdx from 'remark-mdx';
import remarkStringify from 'remark-stringify';
import { parse, stringify } from 'yaml';
import { visit } from 'unist-util-visit';
import { base } from '../site.config.mjs';
import { zellijPages } from '../zellij.config.mjs';

const site = fileURLToPath(new URL('../', import.meta.url));
const repo = resolve(site, '..');
const github = 'https://github.com/lanej/dotfiles';
// All authored content lives in README.md and docs/. This is a route map, not a second manual.
const pages = [
  { file: 'docs/index.mdx', slug: '' },
  { file: 'docs/architecture.mdx', slug: 'architecture' },
  { file: 'docs/components.mdx', slug: 'components' },
  { file: 'docs/design-system.mdx', slug: 'design-system' },
  { file: 'docs/design-system/nord.mdx', slug: 'design-system/nord' },
  { file: 'docs/terminal-workflows.mdx', slug: 'terminal' },
  { file: 'docs/builder.mdx', slug: 'reference/builder' },
  { file: 'docs/documentation-site.mdx', slug: 'maintaining' },
  { file: 'README.md', section: 'Installation', slug: 'reference/install', title: 'Install & set up' },
  { file: 'README.md', section: 'Configuration sets', slug: 'reference/configuration', title: 'Configuration composition' },
  { file: 'docs/zellij.md', slug: 'reference/zellij', title: 'Zellij' },
  { file: 'docs/zellij-keybinds.mdx', slug: 'reference/zellij-keybinds' },
  ...zellijPages,
  { file: 'docs/tmux.md', slug: 'reference/tmux', title: 'tmux sessions' },
  { file: 'docs/stack-darwin.md', slug: 'reference/macos', title: 'macOS stack' },
  { file: 'docs/stack-linux.md', slug: 'reference/linux', title: 'Linux stack' },
  { file: 'docs/rust.md', slug: 'reference/rust', title: 'Rust' },
  { file: 'docs/go-style.md', slug: 'reference/go-style', title: 'Go style guide' },
  { file: 'docs/repository-bootstrap.md', slug: 'reference/repository-bootstrap', title: 'Repository bootstrap' },
];
const headingId = (text) => text.toLowerCase().replaceAll(' ', '-');
const output = resolve(site, 'src/content/docs');
const imageOutput = resolve(site, 'public/source');
await rm(output, { recursive: true, force: true });
await rm(imageOutput, { recursive: true, force: true });
await mkdir(output, { recursive: true });
// Starlight's favicon uses the existing repository logo as a public asset.
await mkdir(resolve(imageOutput, 'docs/brand'), { recursive: true });
await cp(resolve(repo, 'docs/brand/dotfiles-logo.png'), resolve(imageOutput, 'docs/brand/dotfiles-logo.png'));
for (const page of pages) {
  const mdx = page.file.endsWith('.mdx');
  const destination = resolve(output, `${page.slug || 'index'}.${mdx ? 'mdx' : 'md'}`);
  const processor = unified().use(remarkParse).use(remarkGfm).use(remarkStringify);
  if (mdx) processor.use(remarkMdx);
  let source = await readFile(resolve(repo, page.file), 'utf8');
  let metadata = { title: page.title };
  if (mdx) {
    const frontmatter = source.match(/^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/);
    if (!frontmatter) throw new Error(`Missing MDX frontmatter: ${page.file}`);
    metadata = parse(frontmatter[1]);
    source = source.slice(frontmatter[0].length);
  } else if (page.section) {
    const heading = `## ${page.section}\n`;
    const start = source.indexOf(heading);
    if (start === -1) throw new Error(`Missing source section: ${page.section}`);
    source = source.slice(start + heading.length).split('\n## ')[0];
  } else {
    source = source.replace(/^# .*\n/, '');
  }
  const images = new Set();
  function link(url, image = false) {
    if (/^(?:[a-z]+:|\/)/i.test(url)) return url;
    const [path, fragment] = url.split('#');
    const target = path ? relative(repo, resolve(repo, dirname(page.file), path)) : page.file;
    if (image) {
      images.add(target);
      return `${base}/source/${target}`;
    }
    const mapped = pages.find((entry) => entry.file === target && (!entry.section || headingId(entry.section) === fragment));
    if (mapped) return `${base}${mapped.slug ? `/${mapped.slug}/` : '/'}${fragment && !mapped.section ? `#${fragment}` : ''}`;
    if (!path && !page.section) return `#${fragment}`;
    return `${github}/blob/master/${target}${fragment ? `#${fragment}` : ''}`;
  }
  for (const action of metadata.hero?.actions ?? []) action.link = link(action.link);
  for (const key of ['file', 'dark', 'light']) {
    const image = metadata.hero?.image?.[key];
    if (image) metadata.hero.image[key] = relative(dirname(destination), resolve(repo, dirname(page.file), image));
  }
  const tree = processor.parse(source);
  visit(tree, (node) => {
    // Extracted README sections become pages, so their subsections start at h2.
    if (page.section && node.type === 'heading') node.depth -= 1;
    if (['link', 'image', 'definition'].includes(node.type) && node.url) node.url = link(node.url, node.type === 'image');
    // Keep repository-relative links usable inside MDX components as well as prose.
    for (const attribute of node.attributes ?? []) {
      if (attribute.type === 'mdxJsxAttribute' && attribute.name === 'href' && typeof attribute.value === 'string') attribute.value = link(attribute.value);
    }
  });
  for (const image of images) {
    const dest = resolve(imageOutput, image);
    await mkdir(dirname(dest), { recursive: true });
    await cp(resolve(repo, image), dest);
  }
  metadata.editUrl = `${github}/edit/master/${page.file}`;
  await mkdir(dirname(destination), { recursive: true });
  await writeFile(destination, `---\n${stringify(metadata)}---\n\n${processor.stringify(tree)}`);
}
console.log(`Prepared ${pages.length} pages from shared repository Markdown and MDX.`);

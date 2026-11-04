import { readFile, writeFile, mkdir, cp, rm } from 'node:fs/promises';
import { dirname, resolve, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { unified } from 'unified';
import remarkParse from 'remark-parse';
import remarkGfm from 'remark-gfm';
import remarkStringify from 'remark-stringify';
import { visit } from 'unist-util-visit';

const site = fileURLToPath(new URL('../', import.meta.url));
const repo = resolve(site, '..');
const github = 'https://github.com/lanej/dotfiles';
// Existing Markdown stays authoritative. Only this allowlist is published.
const pages = [
  { file: 'README.md', section: 'Installation', slug: 'install', title: 'Install & set up' },
  { file: 'README.md', section: 'Configuration sets', slug: 'configuration', title: 'Configuration composition' },
  { file: 'docs/zellij.md', slug: 'zellij', title: 'Zellij' },
  { file: 'docs/tmux.md', slug: 'tmux', title: 'tmux sessions' },
  { file: 'docs/stack-darwin.md', slug: 'macos', title: 'macOS stack' },
  { file: 'docs/stack-linux.md', slug: 'linux', title: 'Linux stack' },
  { file: 'docs/rust.md', slug: 'rust', title: 'Rust' },
  { file: 'docs/repository-bootstrap.md', slug: 'repository-bootstrap', title: 'Repository bootstrap' },
];
const headingId = (text) => text.toLowerCase().replaceAll(' ', '-');
const processor = unified().use(remarkParse).use(remarkGfm).use(remarkStringify);
const output = resolve(site, 'src/content/docs/reference');
const imageOutput = resolve(site, 'public/source');
await rm(output, { recursive: true, force: true });
await rm(imageOutput, { recursive: true, force: true });
await mkdir(output, { recursive: true });
for (const page of pages) {
  let source = await readFile(resolve(repo, page.file), 'utf8');
  if (page.section) {
    const heading = `## ${page.section}\n`;
    const start = source.indexOf(heading);
    if (start === -1) throw new Error(`Missing source section: ${page.section}`);
    source = source.slice(start + heading.length).split('\n## ')[0];
  } else {
    source = source.replace(/^# .*\n/, '');
  }
  const tree = processor.parse(source);
  const images = [];
  visit(tree, (node) => {
    if (!['link', 'image', 'definition'].includes(node.type) || !node.url) return;
    if (/^(?:[a-z]+:|\/\/)/i.test(node.url)) return;
    const [path, fragment] = node.url.split('#');
    const target = path ? relative(repo, resolve(repo, dirname(page.file), path)) : page.file;
    const mapped = pages.find((entry) => entry.file === target && (!entry.section || headingId(entry.section) === fragment));
    if (node.type === 'image') {
      images.push(target);
      node.url = `/source/${target}`;
    } else if (mapped) {
      node.url = `/reference/${mapped.slug}/${fragment && !mapped.section ? `#${fragment}` : ''}`;
    } else if (!path && !page.section) {
      node.url = `#${fragment}`;
    } else {
      node.url = `${github}/blob/master/${target}${fragment ? `#${fragment}` : ''}`;
    }
  });
  for (const image of images) {
    const dest = resolve(imageOutput, image);
    await mkdir(dirname(dest), { recursive: true });
    await cp(resolve(repo, image), dest);
  }
  const frontmatter = `---\ntitle: ${JSON.stringify(page.title)}\neditUrl: ${github}/edit/master/${page.file}\n---\n\n`;
  await writeFile(resolve(output, `${page.slug}.md`), frontmatter + processor.stringify(tree));
}
console.log(`Prepared ${pages.length} pages from repository documentation.`);

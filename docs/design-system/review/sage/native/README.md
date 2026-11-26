# Sage Midnight native review

Native terminal cell captures from merge checkout `a5bde7aa76031541d1167d044eef25dc3d589953` (PR head `d51e50eafcf85b79c622afd3557aac2f65df6e3d`). SVGs are compact re-encodings of the captured text coordinates, colors, fills, and vector paths. No palette substitutions or invented application contents.

- [Terminal artifact](https://github.com/lanej/dotfiles/actions/runs/45762603064/artifacts/15089574526): fzf, Glow, tmux, CLI.
- [Zellij artifact](https://github.com/lanej/dotfiles/actions/runs/45762602913/artifacts/15090482252): Zellij.

The [bottom capture](https://github.com/lanej/dotfiles/actions/runs/45764616943/artifacts/15091875001) is from merge checkout `836b3f5de0fc722a5e795e47359fe6e873185fda` (head `a46baf1`). Its selected row uses `#5E7067` with `#EEF1EE` ink, verified by the native fixture. Archives also contain original observed cell JSON, raw terminal output and per-preset manifests. These review images do not replace regression baselines or establish native visual acceptance. Neovim, bat and Delta require corrected captures. The tmux capture is now the byte-identical SVG from the [schema-2 native review artifact](https://github.com/lanej/dotfiles/actions/runs/45766113043/artifacts/15092376404), merge checkout `a926c9595ef977f3131dde8f084e29b8500ca66a`. Its compact tabs passed the v1 contract. The complete profile failed, and this does not constitute approval. Studio, Publisher and Kitty require separate native review.

## Acceptance evidence

Schema-2 native review artifacts include the exact palette, independent contract, full observed grids, raw output, SVGs, audits and content hashes. The verifier requires exact deterministic replay; `--gallery-dir` also rejects a missing or altered published image. Except for the exact tmux capture, embedded legacy captures predate that evidence contract and are review references, not verified/approved gallery entries. A complete passing profile can be exported with `--export-gallery`; the export copies original SVG bytes and verifies them again. Replace each from its native artifact without redrawing it.

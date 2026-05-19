# CHANGELOG

<!-- version list -->

## v0.1.0 (2026-05-19)

### Bug Fixes

- **01-04**: CR-01 fix non-seekable BinaryIO crash in sniffer
  ([`f0ded91`](https://github.com/chispa-sideral/contaplus-reader/commit/f0ded912dab7f8ed4f7d220caeaaf8f974440c8a))

- **01-04**: CR-02 guard CLI read_bytes() against OSError
  ([`30d36d1`](https://github.com/chispa-sideral/contaplus-reader/commit/30d36d1568a92b5de6075804f76a961d32ec3d29))

- **01-04**: CR-03 make ContaPlusJournal.rows immutable tuple
  ([`96e57c7`](https://github.com/chispa-sideral/contaplus-reader/commit/96e57c73cbefea32177e69ec53e02944279360ac))

- **01-04**: CR-04 fix mixed-sign both-non-zero guard to use != 0
  ([`744bbef`](https://github.com/chispa-sideral/contaplus-reader/commit/744bbefd141f9ba5359204bdc88d1f5ae8e42491))

- **01-04**: WR-02 fix column width undercount for zero numeric values
  ([`f106121`](https://github.com/chispa-sideral/contaplus-reader/commit/f106121df3f8dfb935bce21ffaa26889f9c7fec9))

- **02**: CR-01/WR-01/WR-02 harden ZIP extraction against zip-slip, symlink and zip-bomb
  ([`22a0708`](https://github.com/chispa-sideral/contaplus-reader/commit/22a0708f78ecc5ab45b2a63c0bbaca2ded10f392))

- **02**: CR-02 coerce numeric SUBCTA cod/titulo fields defensively
  ([`05f4c11`](https://github.com/chispa-sideral/contaplus-reader/commit/05f4c1187efeac6b48019726113c36b7aaa23ffe))

- **02**: WR-01 use literal symlink mode mask, stat.S_IFMT is not a constant
  ([`723cd96`](https://github.com/chispa-sideral/contaplus-reader/commit/723cd96e5dbd0507c97ecae557752cc896757c17))

- **02**: WR-03 make _pick_column case-insensitive internally
  ([`6a2041b`](https://github.com/chispa-sideral/contaplus-reader/commit/6a2041b42224d722f7cb38e363a4efa9202a74d3))

- **02**: WR-04 normalise SUBCTA lookup keys and log enrichment misses
  ([`0f4954b`](https://github.com/chispa-sideral/contaplus-reader/commit/0f4954be1a7fb3f761c13fa2e555aafa57ffbad4))

- **02**: WR-05 carry SUBCTA schema on SubctaTable for full-dump headers
  ([`f036267`](https://github.com/chispa-sideral/contaplus-reader/commit/f0362671e36d53b8161e817ceecfcbc304ef71ba))

- **02**: WR-06 wrap CLI render/write in error handling, no traceback leak
  ([`6ff493d`](https://github.com/chispa-sideral/contaplus-reader/commit/6ff493da37e8cc20cfda92ebabb73db28c43bf33))

- **04**: Set allow_zero_version so PSR honors the 0.1.0 first release (D-04)
  ([`464bcf9`](https://github.com/chispa-sideral/contaplus-reader/commit/464bcf9447e8249a5b4b39ab5a2efaaf7c2fc687))

### Chores

- Add gitignore (excludes confidential pii-test-data)
  ([`66293ae`](https://github.com/chispa-sideral/contaplus-reader/commit/66293aef1475584f300e08379e8fc3f55f61b6d7))

- Add project config
  ([`ff10f34`](https://github.com/chispa-sideral/contaplus-reader/commit/ff10f34e3e8c77186f2209ff933ceb78310bb559))

- **01-03**: README Installation/Usage sections and .gitignore complete
  ([`15dbade`](https://github.com/chispa-sideral/contaplus-reader/commit/15dbaded5acc96e8198df4e8db17603573f00a5a))

- **04**: Point package URLs at the chispa-sideral org
  ([`119b484`](https://github.com/chispa-sideral/contaplus-reader/commit/119b484838ffa301e9425e0708db19c479d3ebe8))

- **04**: Pyproject.toml metadata pass — PEP 639, classifiers, PSR config, typer fix
  (D-04/D-08/D-11/D-12)
  ([`93e1ca6`](https://github.com/chispa-sideral/contaplus-reader/commit/93e1ca67034ffa6703e99edac7d99458ae8ac7db))

### Continuous Integration

- **04**: Add CI workflow — pytest on push and PR
  ([`c90d2fd`](https://github.com/chispa-sideral/contaplus-reader/commit/c90d2fd8a55b864bfd27e7c5f808be6769efa33c))

- **04**: Allow on-demand TestPyPI-only release run
  ([`cf91efa`](https://github.com/chispa-sideral/contaplus-reader/commit/cf91efafb65231918e9eb352d3aaa0f2266c1e08))

- **04**: Skip TestPyPI upload on real releases
  ([`40b1aa9`](https://github.com/chispa-sideral/contaplus-reader/commit/40b1aa9a772f519f6b87176187e78bb5c00bf2b4))

- **04-03**: Add micropip smoke test (D-09) — Pyodide Node.js harness
  ([`96d49a7`](https://github.com/chispa-sideral/contaplus-reader/commit/96d49a7b39bd09f0b88ebbf9381ec8cdff7c47c7))

- **04-03**: Add release.yml — trusted publishing workflow (D-06)
  ([`3c5cdb0`](https://github.com/chispa-sideral/contaplus-reader/commit/3c5cdb00d2fd25b3584b54f5c623f4e1fcee8ad8))

### Documentation

- Capture exploration — lean PWA stack
  ([`110cfb2`](https://github.com/chispa-sideral/contaplus-reader/commit/110cfb233d12720cbc240abb1cb4dee13d922172))

- Create roadmap (5 phases)
  ([`da14ffa`](https://github.com/chispa-sideral/contaplus-reader/commit/da14ffa7f7faa52ce77036a1444c4190cd6c3c78))

- Define v1 requirements
  ([`bfb55e2`](https://github.com/chispa-sideral/contaplus-reader/commit/bfb55e23d82c3233adf7fc60d953992eacd1614d))

- Note confidential real-data fixtures in pii-test-data
  ([`78f759d`](https://github.com/chispa-sideral/contaplus-reader/commit/78f759db87f61613ef85584c306d0844b51ec201))

- Synthesize project research
  ([`2003db1`](https://github.com/chispa-sideral/contaplus-reader/commit/2003db11b273199b26d2923f2a35eb08cf3e236e))

- **01**: Add code review report
  ([`fd59411`](https://github.com/chispa-sideral/contaplus-reader/commit/fd5941175f66e9acbc16ffcece8fbe889986db3c))

- **01**: Add code review report
  ([`c39312f`](https://github.com/chispa-sideral/contaplus-reader/commit/c39312f6fa9b468d747bcae5e5451a6c8435007a))

- **01**: Add gap-closure plan 01-04 for 4 verification blockers
  ([`98344e6`](https://github.com/chispa-sideral/contaplus-reader/commit/98344e61467b4380264553072de58568463de60e))

- **01**: Add phase verification report (gaps found)
  ([`b24b978`](https://github.com/chispa-sideral/contaplus-reader/commit/b24b978c700437f718ab075566bd499c6cba0e60))

- **01**: Capture phase context
  ([`102aeb3`](https://github.com/chispa-sideral/contaplus-reader/commit/102aeb31cde6105401a03ba29850a049e6bcb7ae))

- **01**: Create phase plan
  ([`b3d97f6`](https://github.com/chispa-sideral/contaplus-reader/commit/b3d97f61d70b582bfbf5f44679dfce3133ef0f31))

- **01-01**: Complete journal reader core plan
  ([`57948a0`](https://github.com/chispa-sideral/contaplus-reader/commit/57948a05817c0c5a6d7e625cb1e007674eb5cbe7))

- **01-02**: Complete XLSX renderer and CLI plan
  ([`5414066`](https://github.com/chispa-sideral/contaplus-reader/commit/54140660ed92eb9c49d2258052521b2d997b489b))

- **01-03**: Complete walking skeleton — human-verify APPROVED, Phase 01 done
  ([`0138c87`](https://github.com/chispa-sideral/contaplus-reader/commit/0138c87733f827c10bcbb24447f55ff3ae4939f6))

- **01-03**: Plan task 1 complete — README/gitignore/wheel build verified
  ([`5648332`](https://github.com/chispa-sideral/contaplus-reader/commit/5648332f10d5c50aba5b0e1662256b7dd19a531c))

- **01-04**: Complete gap-closure plan — 5 fixes, 55 tests passing
  ([`4384beb`](https://github.com/chispa-sideral/contaplus-reader/commit/4384beb440ee8ac33ff4d7d5df25c505bb3206ea))

- **02**: Add code review fix report
  ([`5271158`](https://github.com/chispa-sideral/contaplus-reader/commit/52711581014547d699d6dba0c0b4ae3dec4c203f))

- **02**: Add code review report
  ([`c7a8d6d`](https://github.com/chispa-sideral/contaplus-reader/commit/c7a8d6de28d2428790eb1bfd424f62f7af19dee7))

- **02**: Capture phase context
  ([`31e327b`](https://github.com/chispa-sideral/contaplus-reader/commit/31e327b1668ed8356bc73f9539b1b1b88f1bf054))

- **02**: Create phase plan
  ([`ef3e59e`](https://github.com/chispa-sideral/contaplus-reader/commit/ef3e59e897ce4322c70bf16fac4a308630681112))

- **02**: Research phase - ZIP & subaccounts
  ([`fb8a66c`](https://github.com/chispa-sideral/contaplus-reader/commit/fb8a66c1ac479d72ddcf725356c03a7a9bc9bbaa))

- **02-01**: Complete Phase 2 Plan 01 — RED test gate SUMMARY + state update
  ([`ac00a70`](https://github.com/chispa-sideral/contaplus-reader/commit/ac00a70c8f8b4f6f9d50811e21ac0e4020e0fb26))

- **02-02**: Complete ZIP pipeline plan
  ([`55901b6`](https://github.com/chispa-sideral/contaplus-reader/commit/55901b6f22771888135a417810c921156dfd8599))

- **02-03**: Complete multi-sheet XLSX renderer and --company CLI flag plan
  ([`d42d130`](https://github.com/chispa-sideral/contaplus-reader/commit/d42d130580868b0ff8ce59c6c6277c09095b2e29))

- **02-zip-subaccounts**: Create Phase 2 plan — ZIP input, SUBCTA enrichment, multi-sheet XLSX
  ([`a701c61`](https://github.com/chispa-sideral/contaplus-reader/commit/a701c613f8bcdd03950308f5bf5040baeb0e5a06))

- **03**: Add code review report
  ([`86721c5`](https://github.com/chispa-sideral/contaplus-reader/commit/86721c5f307aa4c41db67ec27b509f3a5f7445b8))

- **03**: Add code review report
  ([`d66814f`](https://github.com/chispa-sideral/contaplus-reader/commit/d66814fee6d158aaf21f4244da0f87e1f71fd9a0))

- **03**: Add missing D-NN citations to plans 01-04
  ([`b7f7c97`](https://github.com/chispa-sideral/contaplus-reader/commit/b7f7c97c7e24505fe03421d06c2f2c728647793d))

- **03**: Add phase pattern map
  ([`29a1717`](https://github.com/chispa-sideral/contaplus-reader/commit/29a1717c7c68aba373833ed79808cbe0fee4d73e))

- **03**: Add phase verification report (gaps found)
  ([`8beee93`](https://github.com/chispa-sideral/contaplus-reader/commit/8beee93ea8eef5248ccbd4a758d0f56f7b369cdc))

- **03**: Capture phase context
  ([`7699128`](https://github.com/chispa-sideral/contaplus-reader/commit/7699128b86486008c6fb5f4b1110017e72e62d92))

- **03**: Create gap-closure plan 03-05 for WR-06/WR-05/casing/sheet-count
  ([`c01a33e`](https://github.com/chispa-sideral/contaplus-reader/commit/c01a33e11294ca81a040335fefda71d3d3507a59))

- **03**: Create phase 3 plan — 4 plans, 4 waves
  ([`79ca54d`](https://github.com/chispa-sideral/contaplus-reader/commit/79ca54d5dd208d06da4a834e338eaeb0a02f0b95))

- **03**: Create phase plan
  ([`b8f11c3`](https://github.com/chispa-sideral/contaplus-reader/commit/b8f11c34737878744ede3c1e4eb33ddd5797bdd7))

- **03**: Record gap-closure plan 03-05 in state
  ([`9b3e91e`](https://github.com/chispa-sideral/contaplus-reader/commit/9b3e91e3f05ef551e2b6ded6de18ea31ceb30ed1))

- **03**: Research phase — schemas, trial balance, lenient mechanics
  ([`120cab9`](https://github.com/chispa-sideral/contaplus-reader/commit/120cab9b5b09fc5c6febadd710f4caa7f7ac55d9))

- **03-01**: Complete Phase 3 plan 01 test scaffold summary
  ([`c606450`](https://github.com/chispa-sideral/contaplus-reader/commit/c6064509f5c9f5e9973026e5faa0cf86cf14a36e))

- **03-02**: Complete core models, balance computation, and lenient journal loop plan
  ([`cd735fa`](https://github.com/chispa-sideral/contaplus-reader/commit/cd735fa701e24c917d3cc94d947ae976d0aa3f4d))

- **03-03**: Complete 10-table catalogue, lenient wiring, and balance plan
  ([`98ba477`](https://github.com/chispa-sideral/contaplus-reader/commit/98ba477e55609f2d1c3596915311835d7d2e09a7))

- **03-04**: Complete Phase 3 sheet renderers and lenient CLI plan
  ([`9d3a2c4`](https://github.com/chispa-sideral/contaplus-reader/commit/9d3a2c49943e1f77d05e0d8a0e710c3b05dcdbf2))

- **03-05**: Complete gap-closure plan summary (WR-06/WR-05/casing/sheet-count)
  ([`a69119c`](https://github.com/chispa-sideral/contaplus-reader/commit/a69119cf68eb53aad10e7df500ce42182080a2f7))

- **04**: Add colon-form D-NN decision citations to plan frontmatter
  ([`f20f50a`](https://github.com/chispa-sideral/contaplus-reader/commit/f20f50af0292b0d79f74e87e0e345cf9a94a80fe))

- **04**: Add LICENSE (LGPL-3.0-or-later), expand README into PyPI landing page (D-10/D-11)
  ([`3997aa3`](https://github.com/chispa-sideral/contaplus-reader/commit/3997aa3dbd2a2d8d7bd73d8d4526e5af99eda5f1))

- **04**: Add pattern map
  ([`4cd8b63`](https://github.com/chispa-sideral/contaplus-reader/commit/4cd8b6386bb75a31b23fb9cfc59646f51984c275))

- **04**: Capture phase context
  ([`9a69d10`](https://github.com/chispa-sideral/contaplus-reader/commit/9a69d10a20530c3d21e5378238d3a34ea3bdd92d))

- **04**: Create phase 4 plan — CLI-03 report + PyPI publication
  ([`cd5a0c5`](https://github.com/chispa-sideral/contaplus-reader/commit/cd5a0c54d450a307e6b54abc9ca2442fef0a61e0))

- **04**: Create phase plan
  ([`fbefc65`](https://github.com/chispa-sideral/contaplus-reader/commit/fbefc652e4d11019c773be2556dfc04a4c577a03))

- **04**: Research phase 4 — CLI report, PyPI trusted publishing, micropip gate, PEP 639
  ([`c962e2d`](https://github.com/chispa-sideral/contaplus-reader/commit/c962e2d861b3157f9f209175bcd06619cc90fca0))

- **04-01**: Complete CLI-03 conversion report plan
  ([`c2aa533`](https://github.com/chispa-sideral/contaplus-reader/commit/c2aa5330ca588cf6647c31b7f41123b0818c39ef))

- **04-02**: Complete package metadata plan
  ([`7f2ae66`](https://github.com/chispa-sideral/contaplus-reader/commit/7f2ae66bc5f3ec914890255b936cc17b7a22bd37))

- **04-03**: Complete CI infrastructure plan — release.yml + micropip smoke test
  ([`bdd7d0c`](https://github.com/chispa-sideral/contaplus-reader/commit/bdd7d0c8d487d77a0433a2122f652ce96c06a031))

- **phase-01**: Complete phase execution
  ([`f0025d4`](https://github.com/chispa-sideral/contaplus-reader/commit/f0025d401514b4d39e36c479ab932d516af1c9c9))

- **phase-01**: Evolve PROJECT.md after phase completion
  ([`bfb1d4b`](https://github.com/chispa-sideral/contaplus-reader/commit/bfb1d4b8d02bd6929353b009fd98919fe966b0ed))

- **phase-02**: Add security threat verification
  ([`8019366`](https://github.com/chispa-sideral/contaplus-reader/commit/8019366cecf620d67507c4071f986684fac6a2a7))

- **phase-03**: Add validation strategy
  ([`3985506`](https://github.com/chispa-sideral/contaplus-reader/commit/398550620f9f6b95aa3a32f0d6a71dbc6df92c22))

- **phase-03**: Complete phase execution
  ([`6feed28`](https://github.com/chispa-sideral/contaplus-reader/commit/6feed28859e84233b42ae9396c1f295e002b108e))

- **phase-03**: Evolve PROJECT.md after phase completion
  ([`7696c3d`](https://github.com/chispa-sideral/contaplus-reader/commit/7696c3d59b4ee1dea8a102a40b8b4eec212acae9))

- **phase-03**: Update tracking after wave 1
  ([`caa813c`](https://github.com/chispa-sideral/contaplus-reader/commit/caa813cb4dffa29d854961cd352df5c956a2bc5c))

- **phase-03**: Update tracking after wave 2
  ([`108c61c`](https://github.com/chispa-sideral/contaplus-reader/commit/108c61c79d8b99456282e910857fc6dff9a20a2b))

- **phase-03**: Update tracking after wave 3
  ([`f259943`](https://github.com/chispa-sideral/contaplus-reader/commit/f2599435290b19478ffc6385f2eddbd70bfbb60c))

- **phase-03**: Update tracking after wave 4
  ([`88a94c6`](https://github.com/chispa-sideral/contaplus-reader/commit/88a94c671687e7ceaf5522d0f75bc5e063757606))

- **phase-03**: Update tracking after wave 5
  ([`529a39d`](https://github.com/chispa-sideral/contaplus-reader/commit/529a39d27454427d882bd58839f8bda3203c3647))

- **phase-1**: Add validation strategy
  ([`5160223`](https://github.com/chispa-sideral/contaplus-reader/commit/5160223f1cea0ae913e1db94beb90d8c01876809))

- **phase-1**: Research journal slice domain
  ([`df303d1`](https://github.com/chispa-sideral/contaplus-reader/commit/df303d1dae08dfe3f19c66a4a792502d7a98a9cd))

- **phase-2**: Add validation strategy
  ([`125083e`](https://github.com/chispa-sideral/contaplus-reader/commit/125083e6892687d0fac4ed32b92e1248b7e21ed7))

- **phase-2**: Refresh validation strategy after Nyquist audit
  ([`2b1ca34`](https://github.com/chispa-sideral/contaplus-reader/commit/2b1ca345d4619ca9158563c2f30e3c842fb2df23))

- **phase-4**: Add validation strategy
  ([`d16161c`](https://github.com/chispa-sideral/contaplus-reader/commit/d16161c65bf275c341d8a1ce643d4225bf46bd12))

- **state**: Record phase 1 context session
  ([`21e5948`](https://github.com/chispa-sideral/contaplus-reader/commit/21e5948f07a5cebfd750895683a6da2146a1d4bc))

- **state**: Record phase 2 context session
  ([`6062e3a`](https://github.com/chispa-sideral/contaplus-reader/commit/6062e3a3f0dd0d055d61eb37b1e55f051582f603))

- **state**: Record phase 3 context session
  ([`8b26c05`](https://github.com/chispa-sideral/contaplus-reader/commit/8b26c055e197e0d8bb288135484f1cd5d7ed89d9))

- **state**: Record phase 4 context session
  ([`ac7e588`](https://github.com/chispa-sideral/contaplus-reader/commit/ac7e58885d51523ebf19b194c8a9756a4c714c7a))

### Features

- **01-01**: Journal reader with D-A1...D-E3 business rules
  ([`fe13755`](https://github.com/chispa-sideral/contaplus-reader/commit/fe13755e5dad378acb0d81a5eb7bad797db32853))

- **01-01**: Package scaffold, models, bridge, and sniffer
  ([`1e7ee62`](https://github.com/chispa-sideral/contaplus-reader/commit/1e7ee620690f312fb2074a9f169303ab13e9ed6e))

- **01-01**: Synthetic fixture factory and ported reader test suite
  ([`ce3e785`](https://github.com/chispa-sideral/contaplus-reader/commit/ce3e7853538298634a46d4251fb5519a15603d8c))

- **01-02**: Implement Typer CLI entry point (contaplus2xlsx)
  ([`2427c38`](https://github.com/chispa-sideral/contaplus-reader/commit/2427c38e42835256d8cfb772e2399001569e8ded))

- **01-02**: Implement XLSX renderer with accounting format and Spanish headers
  ([`ba250d0`](https://github.com/chispa-sideral/contaplus-reader/commit/ba250d0a7e76f79e1c8bf88c3df9923bd0afb46d))

- **02-02**: Extend models, upgrade sniffer, add _zip.py and _subcta.py
  ([`229845f`](https://github.com/chispa-sideral/contaplus-reader/commit/229845f2cc28841597fc71e92ad53b88b2216d02))

- **02-02**: Wire ZIP dispatch in _reader.py and __init__.py; all reader tests GREEN
  ([`deb3a63`](https://github.com/chispa-sideral/contaplus-reader/commit/deb3a6395b586d215c4d464f3c15cbf9c8a70af6))

- **02-03**: Add --company flag to CLI and wire render(data) for multi-sheet output
  ([`ae75d05`](https://github.com/chispa-sideral/contaplus-reader/commit/ae75d055582749114949e6cbb37c2285ea19cef2))

- **02-03**: Generalize xlsx.py to render(ContaPlusData) with multi-sheet and Descripción
  ([`d3ec20c`](https://github.com/chispa-sideral/contaplus-reader/commit/d3ec20cb1297c1f8810e38eec21282bee17e60b2))

- **03-02**: Create _balance.py with compute_balance Decimal accumulation
  ([`3f73a7c`](https://github.com/chispa-sideral/contaplus-reader/commit/3f73a7c5981215b8f093d5aa55ade84362184b68))

- **03-02**: Extend _reader.py and read() with lenient journal loop
  ([`dec8433`](https://github.com/chispa-sideral/contaplus-reader/commit/dec8433eae03367b6f5d1a6ae59aab80fe45123a))

- **03-02**: Extend models.py with Phase 3 types and ContaPlusData attributes
  ([`df99913`](https://github.com/chispa-sideral/contaplus-reader/commit/df99913563c104a24cf16d59675bc95932afa183))

- **03-03**: Wire full 10-table catalogue, lenient path, and balance into read()
  ([`9843c81`](https://github.com/chispa-sideral/contaplus-reader/commit/9843c816945285da0eb28e1f1c98ee09e22b807f))

- **03-04**: Add --lenient flag to CLI and problems count to one-line summary
  ([`132e046`](https://github.com/chispa-sideral/contaplus-reader/commit/132e046df622cd5905ab2369b28a8ec2d5966337))

- **03-04**: Add Phase 3 sheet renderers and update render() sheet order
  ([`8267582`](https://github.com/chispa-sideral/contaplus-reader/commit/8267582cff76f7cb58d0863c398c652d16e26df1))

- **03-05**: Fix render() crash on journal=None (WR-06)
  ([`38cc316`](https://github.com/chispa-sideral/contaplus-reader/commit/38cc31680c8058552879d40262558824aa50dd80))

- **03-05**: Fix WR-05 ValueError catch, canonicalize ProblemEntry.table, fix CLI sheet count
  ([`2d1a8f6`](https://github.com/chispa-sideral/contaplus-reader/commit/2d1a8f6c57be79ff9b7f4612ea9c040c18b47818))

- **04-01**: Implement _print_report() replacing D-16 one-liner (CLI-03 GREEN)
  ([`c9c9fed`](https://github.com/chispa-sideral/contaplus-reader/commit/c9c9fedc42372d194ec52fbe64ec0bc98e5b1729))

### Testing

- **01-02**: Add failing tests for CLI entry point (RED)
  ([`1d3d326`](https://github.com/chispa-sideral/contaplus-reader/commit/1d3d3267b7d4d3139de0d2d0bd10823b2fef4345))

- **01-02**: Add failing tests for XLSX renderer (RED)
  ([`363e74f`](https://github.com/chispa-sideral/contaplus-reader/commit/363e74f9faf48b183264622e5f12778e3d83bf4a))

- **02**: Complete UAT - 3 passed, 0 issues
  ([`fb5ebb0`](https://github.com/chispa-sideral/contaplus-reader/commit/fb5ebb00bae563d2b437842570b5be7ccc55fbbd))

- **02**: Persist human verification items as UAT
  ([`9aeebee`](https://github.com/chispa-sideral/contaplus-reader/commit/9aeebee84fb3027ee7590e0aabf38d6e3378f6a6))

- **02-01**: Add failing Phase 2 tests for ZIP read, SUBCTA enrichment, multi-sheet
  ([`4307696`](https://github.com/chispa-sideral/contaplus-reader/commit/4307696cc264eec0293c29f6f7ba2baf5cb1ba56))

- **02-01**: Extend conftest.py with Phase 2 ZIP and table fixture builders
  ([`7e88540`](https://github.com/chispa-sideral/contaplus-reader/commit/7e8854057351149f8e90d06e957d5194c4e4d7c9))

- **02-03**: Add failing tests for render() multi-sheet and Descripción column
  ([`73da9e7`](https://github.com/chispa-sideral/contaplus-reader/commit/73da9e7cca8e9b4934aa6e897ec87816526c66cb))

- **02-03**: Remove xfail markers from CLI company-flag tests
  ([`dc28ba5`](https://github.com/chispa-sideral/contaplus-reader/commit/dc28ba502b931172ef0821530d179fd766f77965))

- **03-01**: Add failing Phase 3 test files (RED state)
  ([`114da3b`](https://github.com/chispa-sideral/contaplus-reader/commit/114da3b32c55397ce8a9e980da56e5959b55e161))

- **03-01**: Extend conftest.py with Phase 3 synthetic fixtures
  ([`3a914c0`](https://github.com/chispa-sideral/contaplus-reader/commit/3a914c03624ced67157812eae0fbd09a6d0cf7b6))

- **03-05**: Add failing tests for render(journal=None) WR-06 fix and D-03 end-to-end
  ([`0e36ea6`](https://github.com/chispa-sideral/contaplus-reader/commit/0e36ea653192d45abc3f6b2af25e473cd8becff3))

- **03-05**: Add failing tests for WR-05 ValueError per-row catch
  ([`9a2c2fb`](https://github.com/chispa-sideral/contaplus-reader/commit/9a2c2fb44ac5b90d097d59ab32e2901695a2589e))

- **04**: Strip ANSI codes before --help option assertion
  ([`88cfc2b`](https://github.com/chispa-sideral/contaplus-reader/commit/88cfc2b10d0af50b78ade615fe22fd04753f0555))

- **04-01**: Add diario_with_memo_dbf fixture + CLI-03 RED tests
  ([`053d15c`](https://github.com/chispa-sideral/contaplus-reader/commit/053d15ca7cbb8c258568011af7f978e67383f1ef))


## v0.0.0 (2026-05-15)

- Initial Release

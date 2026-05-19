import { loadPyodide } from "pyodide";

async function main() {
  const pyodide = await loadPyodide();

  // micropip must be loaded before use (it is a Pyodide package itself)
  await pyodide.loadPackage("micropip");
  const micropip = pyodide.pyimport("micropip");

  // micropip resolves contaplus-reader's deps (pandas, openpyxl, dbfread):
  //   pandas/numpy (pre-compiled Pyodide packages) → micropip calls loadPackage internally
  //   openpyxl and dbfread (pure-Python PyPI wheels) → micropip fetches from PyPI
  // When WHEEL_URL is set (local pre-publish testing), use it instead of the PyPI package name.
  const packageRef = process.env.WHEEL_URL || "contaplus-reader";
  await micropip.install(packageRef);

  // Minimal import smoke test — confirms the public API is accessible
  await pyodide.runPythonAsync(`
    import contaplus_reader
    from contaplus_reader import read, ContaPlusReadError
    print("contaplus-reader imported successfully")
  `);

  console.log("Smoke test PASSED");
}

main().catch((e) => { console.error(e); process.exit(1); });

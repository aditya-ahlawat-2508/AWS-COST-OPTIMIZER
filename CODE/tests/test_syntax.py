import pathlib
import py_compile

LAMBDA_DIR = pathlib.Path(__file__).parent.parent / "lambda_"


def test_all_lambda_files_compile():
    # Would have caught the SyntaxError in cost_explorer.py that broke every
    # Lambda action (handler.py imports the module at the top of the file).
    py_files = list(LAMBDA_DIR.glob("*.py"))
    assert py_files, "expected to find lambda_ source files"
    for path in py_files:
        py_compile.compile(str(path), doraise=True)

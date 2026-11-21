import runpy

def test_example():
    assert runpy.run_path('src/example.py')['value'] == 1

default_test_code = r"""
import os, subprocess
cmd = 'git diff --name-only'
output = subprocess.check_output(cmd, shell=True).decode('utf-8')
for line in output.splitlines():
    file_name = line.split('/')[-1]
    cmd = f'find . -name test_{file_name}'
    output = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
    if output:
        cmd = f'pytest -x {output}'
        print('Running:', cmd)
        return_code = subprocess.run(cmd, shell=True).returncode
        assert return_code == 0
"""

custom_pytest_code = """
import subprocess
cmd = 'pytest -x {file_name}'
print('Running:', cmd)
return_code = subprocess.run(cmd, shell=True).returncode
assert return_code == 0
"""

custom_test_code = """
import subprocess
cmd = '{cmd}'
print('Running:', cmd)
return_code = subprocess.run(cmd, shell=True).returncode
assert return_code == 0
"""


def get_test_code(instance_id: str):
    test_codes = {
        'astropy__astropy-12907': """
from astropy.modeling import models as m
from astropy.modeling.separable import separability_matrix

cm = m.Linear1D(10) & m.Linear1D(5)

a= separability_matrix(m.Pix2Sky_TAN() & cm)

import numpy as np

expected_matrix = np.array([[ True,  True, False, False],
                            [ True,  True, False, False],
                            [False, False,  True,  False],
                            [False, False,  False,  True]])

assert np.array_equal(a, expected_matrix), "Matrix does not match expected structure"
""",
        'astropy__astropy-14182': r"""
lines = '''
===== ========
 wave response
   nm       ct
===== ========
350.0      0.7
950.0      1.2
===== ========
'''.strip().splitlines()
from astropy.table import QTable
import astropy.units as u
from io import StringIO

tbl = QTable({'wave': [350, 950] * u.nm, 'response': [0.7, 1.2]*u.count})

out = StringIO()
tbl.write(out,  format="ascii.rst", header_rows=["name", "unit"])
actual,expected=out.getvalue().splitlines(),lines
if actual != expected:
    print("Expected:")
    print('\\n'.join(expected))
    print("Got:")
    print('\\n'.join(actual))
    import difflib
    print('Diff:')
    for line in difflib.unified_diff(actual, expected, fromfile='actual output', tofile='expected output', lineterm=''):
        print(line)

    assert actual == expected, "Output does not match expected structure"
""",
        'astropy__astropy-14539': r"""
from astropy.io import fits
col = fits.Column('a', format='QD', array=[[0], [0, 0]])
hdu = fits.BinTableHDU.from_columns([col])
hdu.writeto('/testbed/diffbug.fits', overwrite=True)

print(fits.FITSDiff('diffbug.fits', 'diffbug.fits').identical)
fits.printdiff('diffbug.fits', 'diffbug.fits')
assert fits.FITSDiff('diffbug.fits', 'diffbug.fits').identical
""",
        'django__django-11133': r"""from django.conf import settings;
settings.configure(DEFAULT_CHARSET='utf-8');
from django.http import HttpResponse
# memoryview content
response = HttpResponse(memoryview(b"My Content"))
if response.content != b"My Content":
    print(response.content)

assert response.content == b"My Content"
""",
        'psf__requests-2317': r"""
import requests

url = "https://httpbin.org/get"
method = b'GET'
response = requests.request(method, url)
if response.status_code != 200:
    print('Status code:', response.status_code)
assert response.status_code == 200
""",
        'sympy__sympy-13647': r"""
import sympy as sm
M = sm.eye(6)
V = 2 * sm.ones(6, 2)
result = M.col_insert(3, V)
assert result == sm.Matrix([[1, 0, 0, 2, 2, 0, 0, 0], [0, 1, 0, 2, 2, 0, 0, 0], [0, 0, 1, 2, 2, 0, 0, 0], [0, 0, 0, 2, 2, 1, 0, 0], [0, 0, 0, 2, 2, 0, 1, 0], [0, 0, 0, 2, 2, 0, 0, 1]])
""",
        # MOD: (Piecewise((x, y > x), (y, True)) / z) % 1 added extra; not given in statement
        'sympy__sympy-21379': r"""
from sympy import *

x, y, z = symbols('x y z', real=True)

# (Piecewise((x, y > x), (y, True)) / z) % 1
expr = exp(sinh(Piecewise((x, y > x), (y, True)) / z))
print(expr.subs({1: 1.0}))

""",
        'sympy__sympy-22714': r"""
import sympy as sp
with sp.evaluate(False):
  sp.S('Point2D(Integer(1),Integer(2))')
""",
        'sympy__sympy-23262': r"""
from sympy import lambdify
import inspect

output = inspect.getsource(lambdify([], tuple([1])))
assert output == 'def _lambdifygenerated():\\n    return (1,)\\n', f'Got:\\n{output}'
""",
        'sympy__sympy-24066': r"""
from sympy import exp
from sympy.physics import units
from sympy.physics.units.systems.si import SI

expr = units.second / (units.ohm * units.farad)
dim = SI._collect_factor_and_dimension(expr)[1]

assert SI.get_dimension_system().is_dimensionless(dim)

buggy_expr = 100 + exp(expr)
print(SI._collect_factor_and_dimension(buggy_expr))
""",
        'scikit-learn__scikit-learn-13142': r"""
import numpy as np
from sklearn.mixture import GaussianMixture
from sklearn.utils.testing import assert_array_equal
X = np.random.randn(1000, 5)
gm = GaussianMixture(n_components=5, n_init=5)
c1 = gm.fit_predict(X)
c2 = gm.predict(X)
assert_array_equal(c1, c2)
""",
        'scikit-learn__scikit-learn-14087': r"""
import sys
import sklearn
from sklearn.linear_model import LogisticRegressionCV
import numpy as np

np.random.seed(29)
X = np.random.normal(size=(1000, 3))
beta = np.random.normal(size=3)
intercept = np.random.normal(size=None)
y = np.sign(intercept + X @ beta)

LogisticRegressionCV(cv=5, solver='saga', tol=1e-2, refit=False).fit(X, y)
""",
        'scikit-learn__scikit-learn-14983': r"""
from sklearn.model_selection import RepeatedKFold, RepeatedStratifiedKFold
cond = repr(RepeatedKFold()) == 'RepeatedKFold(n_splits=5, n_repeats=10, random_state=None)'
if not cond:
    print(repr(RepeatedKFold()))
    assert repr(RepeatedKFold()) == 'RepeatedKFold(n_splits=5, n_repeats=10, random_state=None)'
cond = repr(RepeatedStratifiedKFold()) == 'RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=None)'
if not cond:
    print(repr(RepeatedStratifiedKFold()))
    assert repr(RepeatedStratifiedKFold()) == 'RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=None)'
""",
        'pytest-dev__pytest-7432': default_test_code,
        'matplotlib__matplotlib-25332': custom_pytest_code.format(
            file_name='lib/matplotlib/tests/test_pickle.py'
        ),
        'django__django-12708': custom_test_code.format(
            cmd='/testbed/tests/runtests.py test migrations.test_operations.OperationTests.test_alter_unique_together  --parallel 1'
        ),
        'pydata__xarray-4094': """import xarray as xr
import numpy as np

arr = xr.DataArray(
    np.arange(3),
    coords=[("x", [0, 1, 2])],
)
data = xr.Dataset({"a": arr, "b": arr})
stacked = data.to_stacked_array('y', sample_dims=['x'])
unstacked = stacked.to_unstacked_dataset('y')
print(unstacked)
"""
        + custom_pytest_code.format(
            file_name='xarray/tests/test_dataset.py::TestDataset::test_to_stacked_array_to_unstacked_dataset_different_dimension'
        ),
        # 'matplotlib__matplotlib-24970': default_test_code,
        'sympy__sympy-12419': """
from sympy import *
from sympy import Q as Query

n = Symbol('n', integer=True, positive=True)
i, j = symbols('i j', integer=True)
M = MatrixSymbol('M', n, n)

e = None
with assuming(Query.orthogonal(M)):
    e = refine((M.T * M).doit())

# Correct: M.T * M is an identity matrix.
print(e, e[0, 0], e[0, 1], e[1, 0], e[1, 1])

# Correct: The output is True True
print(ask(Query.diagonal(e)), ask(Query.integer_elements(e)))

# Correct: The sum of the diagonal elements is n
print(Sum(e[i, i], (i, 0, n-1)).doit())

# So far so good
# Total sum of the elements is expected to be 'n' but the answer is 0!
assert Sum(Sum(e[i, j], (i, 0, n-1)), (j, 0, n-1)).doit() != 0
""",
        'sympy__sympy-17655': custom_test_code.format(
            cmd='bin/test sympy/geometry/tests/test_point.py'
        ),
        'django__django-13590': custom_test_code.format(
            cmd='tests/runtests.py expressions.tests.IterableLookupInnerExpressionsTests.test_complex_expressions_do_not_introduce_sql_injection_via_untrusted_string_inclusion && tests/runtests.py expressions.tests.IterableLookupInnerExpressionsTests.test_range_lookup_allows_F_expressions_and_expressions_for_integers'
        ),
        'django__django-14787': custom_test_code.format(
            cmd='tests/runtests.py decorators.tests.MethodDecoratorTests.test_new_attribute'
        ),
        'sympy__sympy-16792': """from sympy.utilities.autowrap import autowrap
from sympy import MatrixSymbol
import numpy as np

x = MatrixSymbol('x', 2, 1)
expr = 1.0
f = autowrap(expr, args=(x,), backend='cython')

f(np.array([[1.0, 2.0]]))""",
        'matplotlib__matplotlib-23476': """
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import pickle



def dump_load_get_dpi(fig):
    with open('sinus.pickle','wb') as file:
        pickle.dump(fig, file)

    with open('sinus.pickle', 'rb') as blob:
        fig2 = pickle.load(blob)
    return fig2, fig2.dpi


def run():
    fig = plt.figure()
    x = np.linspace(0,2*np.pi)
    y = np.sin(x)
    initial_dpi = fig.dpi
    for i in range(32):
        print(f'{i}: {fig.dpi}')
        fig, dpi = dump_load_get_dpi(fig)
        assert fig.dpi == initial_dpi, f'Got {fig.dpi}'


if __name__ == '__main__':
    run()
""",
        'django__django-11848': custom_test_code.format(
            cmd='tests/runtests.py utils_tests.test_http.HttpDateProcessingTests.test_parsing_rfc850'
        ),
        'django__django-13964': custom_test_code.format(
            cmd='tests/runtests.py  many_to_one.tests.ManyToOneTests.test_cached_foreign_key_with_to_field_not_cleared_by_save '
        ),
        'django__django-14155': custom_test_code.format(
            cmd='tests/runtests.py urlpatterns_reverse.tests.ResolverMatchTests.test_repr'
        ),
        'django__django-14534': custom_test_code.format(
            cmd='tests/runtests.py forms_tests.tests.test_forms.FormsTestCase.test_iterable_boundfield_select'
        ),
        'django__django-15695': custom_test_code.format(
            cmd='tests/runtests.py migrations.test_operations.OperationTests.test_rename_index_unnamed_index && tests/runtests.py migrations.test_operations.OperationTests.test_rename_index_unknown_unnamed_index'
        ),
        'astropy__astropy-14365': custom_pytest_code.format(
            file_name='astropy/io/ascii/tests/test_qdp.py'
        ),
        'matplotlib__matplotlib-23299': custom_pytest_code.format(
            file_name='lib/matplotlib/tests/test_rcparams.py'
        ),
        'sympy__sympy-18698': """
from sympy import symbols, sqf_list
x = symbols('x')
p = (x**2 + 1) * (x - 1)**2 * (x - 2)**3 * (x - 3)**3
expected = (1, [(x**2 + 1, 1), (x - 1, 2), (x**2 - 5*x + 6, 3)])
assert sqf_list(p) == expected, f'Got {sqf_list(p)}, expected {expected}'
""",
        'matplotlib__matplotlib-23299': custom_pytest_code.format(
            file_name='lib/matplotlib/tests/test_rcparams.py::test_rcparams'
        ),
        'django__django-15252': custom_test_code.format(
            cmd='tests/runtests.py backends.base.test_creation'
        ),
        'sphinx-doc__sphinx-11445': custom_pytest_code.format(
            file_name='tests/test_util_rst.py'
        ),
        'astropy__astropy-16898': '''
import numpy as np
from astropy.io import fits
from astropy.table import QTable, Table
data = np.array([("", 12)], dtype=[("a", "S"), ("b", "i4")])
fits.BinTableHDU(data).writeto("zerodtable.fits", overwrite=True)
t = Table.read("zerodtable.fits")
t
'''
    }
    return test_codes.get(instance_id, '')


if __name__ == '__main__':
    print(get_test_code('django__django-11133'))

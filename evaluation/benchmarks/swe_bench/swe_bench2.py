def update_issue_description(description: str, instance_id: str) -> str:
    description = description.replace('\r\n', '\n')
    if instance_id == 'astropy__astropy-14182':
        actual = """Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/usr/lib/python3/dist-packages/astropy/table/connect.py", line 129, in __call__
    self.registry.write(instance, *args, **kwargs)
  File "/usr/lib/python3/dist-packages/astropy/io/registry/core.py", line 369, in write
    return writer(data, *args, **kwargs)
  File "/usr/lib/python3/dist-packages/astropy/io/ascii/connect.py", line 26, in io_write
    return write(table, filename, **kwargs)
  File "/usr/lib/python3/dist-packages/astropy/io/ascii/ui.py", line 856, in write
    writer = get_writer(Writer=Writer, fast_writer=fast_writer, **kwargs)
  File "/usr/lib/python3/dist-packages/astropy/io/ascii/ui.py", line 800, in get_writer
    writer = core._get_writer(Writer, fast_writer, **kwargs)
  File "/usr/lib/python3/dist-packages/astropy/io/ascii/core.py", line 1719, in _get_writer
    writer = Writer(**writer_kwargs)
TypeError: RST.__init__() got an unexpected keyword argument 'header_rows"""
        expected = """Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/usr/lib/python3/dist-packages/astropy/table/connect.py", line 130, in __call__
    self.registry.write(instance, *args, **kwargs)
  File "/usr/lib/python3/dist-packages/astropy/io/registry/core.py", line 385, in write
    return writer(data, *args, **kwargs)
  File "/usr/lib/python3/dist-packages/astropy/io/ascii/connect.py", line 28, in io_write
    return write(table, filename, **kwargs)
  File "/usr/lib/python3/dist-packages/astropy/io/ascii/ui.py", line 975, in write
    writer = get_writer(Writer=Writer, fast_writer=fast_writer, **kwargs)
  File "/usr/lib/python3/dist-packages/astropy/io/ascii/ui.py", line 901, in get_writer
    writer = core._get_writer(Writer, fast_writer, **kwargs)
  File "/usr/lib/python3/dist-packages/astropy/io/ascii/core.py", line 1815, in _get_writer
    writer = Writer(**writer_kwargs)
TypeError: RST.__init__() got an unexpected keyword argument 'header_rows"""
        print('Updating issue description')
        return description.replace(actual, expected)

    elif instance_id == 'astropy__astropy-13236':
        actual = '- Add a FutureWarning here telling the user to wrap `data` in `Column` and that in the future (5.2) the structured array will be added as a `Column`.\n'
        return description.replace(actual, '')
    elif instance_id == 'astropy__astropy-14995':
        actual = '...'
        expected1 = """Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/testbed/astropy/nddata/mixins/ndarithmetic.py", line 618, in multiply
    return self._prepare_then_do_arithmetic(
  File "/testbed/astropy/nddata/mixins/ndarithmetic.py", line 731, in _prepare_then_do_arithmetic
    result, init_kwds = operand._arithmetic(operation, operand2, **kwargs)
  File "/testbed/astropy/nddata/mixins/ndarithmetic.py", line 335, in _arithmetic
    kwargs["mask"] = self._arithmetic_mask(
  File "/testbed/astropy/nddata/mixins/ndarithmetic.py", line 527, in _arithmetic_mask
    return handle_mask(self.mask, operand.mask, **kwds)
TypeError: unsupported operand type(s) for |: 'int' and 'NoneType'
"""
        expected2 = """Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/testbed/astropy/nddata/mixins/ndarithmetic.py", line 618, in multiply
    return self._prepare_then_do_arithmetic(
  File "/testbed/astropy/nddata/mixins/ndarithmetic.py", line 734, in _prepare_then_do_arithmetic
    result, init_kwds = cls._arithmetic(
  File "/testbed/astropy/nddata/mixins/ndarithmetic.py", line 335, in _arithmetic
    kwargs["mask"] = self._arithmetic_mask(
  File "/testbed/astropy/nddata/mixins/ndarithmetic.py", line 527, in _arithmetic_mask
    return handle_mask(self.mask, operand.mask, **kwds)
TypeError: unsupported operand type(s) for |: 'int' and 'NoneType'
"""
        for expected in [expected1, expected2]:
            description = description.replace(actual, expected, 1)
    elif instance_id == 'scikit-learn__scikit-learn-13779':
        actual = "AttributeError: 'NoneType' object has no attribute 'fit'"
        expected = """Traceback (most recent call last):
  File "test_task.py", line 15, in <module>
    voter.fit(X, y, sample_weight=np.ones(y.shape))
  File "/testbed/sklearn/ensemble/voting.py", line 273, in fit
    return super().fit(X, transformed_y, sample_weight)
  File "/testbed/sklearn/ensemble/voting.py", line 81, in fit
    if not has_fit_parameter(step, 'sample_weight'):
  File "/testbed/sklearn/utils/validation.py", line 808, in has_fit_parameter
    return parameter in signature(estimator.fit).parameters
AttributeError: 'NoneType' object has no attribute 'fit'"""
        return description.replace(actual, expected)

    elif instance_id == 'matplotlib__matplotlib-24970':
        return description + '\nEnable the warnings e.g., python -W always <file>.py'
    elif instance_id == 'django__django-12708':
        description = description.replace('378', '411')
        traceback = """Traceback (most recent call last):
  ...
  File "/testbed/django/db/backends/base/schema.py", line 396, in alter_index_together
    self._delete_composed_index(model, fields, {'index': True}, self.sql_delete_index)
  File "/testbed/django/db/backends/base/schema.py", line 414, in _delete_composed_index
    ", ".join(columns),
ValueError: Found wrong number (2) of constraints for my_app_mymodel(field1, field2)"""
        return description + '\n' + traceback
    elif instance_id == 'django__django-14155':
        return description.replace(
            'ISTM that we can simply unwrap functools.partial objects in ResolverMatch.__init__().',
            '',
        )
    elif instance_id == 'scikit-learn__scikit-learn-14087':
        actual = """~/.pyenv/versions/3.6.7/envs/jupyter/lib/python3.6/site-packages/sklearn/linear_model/logistic.py in fit(self, X, y, sample_weight)
   2192                 else:
   2193                     w = np.mean([coefs_paths[:, i, best_indices[i], :]
-> 2194                                  for i in range(len(folds))], axis=0)
   2195
   2196                 best_indices_C = best_indices % len(self.Cs_)

~/.pyenv/versions/3.6.7/envs/jupyter/lib/python3.6/site-packages/sklearn/linear_model/logistic.py in <listcomp>(.0)
   2192                 else:
   2193                     w = np.mean([coefs_paths[:, i, best_indices[i], :]
-> 2194                                  for i in range(len(folds))], axis=0)
   2195
   2196                 best_indices_C = best_indices % len(self.Cs_)"""
        expected = """~/.pyenv/versions/3.6.7/envs/jupyter/lib/python3.6/site-packages/sklearn/linear_model/logistic.py in fit(self, X, y, sample_weight)
   2176                 else:
   2177                     w = np.mean([coefs_paths[:, i, best_indices[i], :]
-> 2178                                  for i in range(len(folds))], axis=0)
   2179
   2180                 best_indices_C = best_indices % len(self.Cs_)

~/.pyenv/versions/3.6.7/envs/jupyter/lib/python3.6/site-packages/sklearn/linear_model/logistic.py in <listcomp>(.0)
   2176                 else:
   2177                     w = np.mean([coefs_paths[:, i, best_indices[i], :]
-> 2178                                  for i in range(len(folds))], axis=0)
   2179
   2180                 best_indices_C = best_indices % len(self.Cs_)"""
        return description.replace(actual, expected)
    elif instance_id == 'sympy__sympy-15345':
        # https://www.all-hands.dev/share?share_id=550481ee897e24d342e376406560794315d09b6a16b2dd1ab1c1ab46a30db88b
        return description.replace('x,2', '2,x')
    elif instance_id == 'pydata__xarray-4094':
        traceback = """Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/testbed/xarray/core/dataarray.py", line 1972, in to_unstacked_dataset
    return Dataset(data_dict)
  File "/testbed/xarray/core/dataset.py", line 543, in __init__
    variables, coord_names, dims, indexes, _ = merge_data_and_coords(
  File "/testbed/xarray/core/merge.py", line 466, in merge_data_and_coords
    return merge_core(
  File "/testbed/xarray/core/merge.py", line 597, in merge_core
    variables, out_indexes = merge_collected(collected, prioritized, compat=compat)
  File "/testbed/xarray/core/merge.py", line 228, in merge_collected
    merged_vars[name] = unique_variable(name, variables, compat)
  File "/testbed/xarray/core/merge.py", line 142, in unique_variable
    raise MergeError(
xarray.core.merge.MergeError: conflicting values for variable 'y' on objects to be combined. You can skip this check by specifying compat='override'.
"""
        return description # + '\n' + traceback
    elif instance_id == 'sympy__sympy-12419':
        return '''
from sympy import Identity, symbols

n = 3
i, j = symbols('i j', integer=True)
I = Identity(n)

print(I[0, 0])  # Correctly returns 1
print(I[0, 1])  # Correctly returns 0
print(I[i, j])  # Incorrectly returns 0 for symbolic indices
'''
    elif instance_id == 'sympy__sympy-17630':
        return '''from sympy import *
z = ZeroMatrix(2, 2)
print(type(Add(z, z)))
# Should return ZeroMatrix but returns <class 'sympy.core.numbers.Zero'>
'''
    elif instance_id == 'sympy__sympy-21612':
        return '''>>> from sympy.parsing.latex import parse_latex
>>> parse_latex("\\frac{a}{\\frac{1}{b}}")
a/1/b

Expected:
a/(1/b)
'''
    elif instance_id == 'pylint-dev__pylint-7080':
        return '''% cat src/gen/test.py 
import bla

% pylint --version
pylint 2.13.9
astroid 2.11.5
Python 3.9.13 (main, May 24 2022, 21:28:31) 
[Clang 13.1.6 (clang-1316.0.21.2)]

% cat pyproject.toml 
[tool.pylint.MASTER]
ignore-paths = [
  # Auto generated
  "^src/gen/.*$", 
]


## Succeeds as expected                                                                                                                                                                                                                                                                           
% pylint --recursive=y src/

## Fails for some reason
% pylint --recursive=y .   
************* Module test
src/gen/test.py:1:0: C0114: Missing module docstring (missing-module-docstring)
src/gen/test.py:1:0: E0401: Unable to import 'bla' (import-error)
src/gen/test.py:1:0: W0611: Unused import bla (unused-import)

------------------------------------------------------------------
The issue is that pylint is failing when run recursively from the root directory (`.`) but succeeds when run from the `src/` directory.
'''
    return description

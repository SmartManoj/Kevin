from openhands.runtime.plugins import AgentSkillsRequirement

_AGENT_SKILLS_DOCS = AgentSkillsRequirement.documentation

COMMAND_DOCS = (
    '\nApart from the standard Python library, the assistant can also use the following functions (already imported) in <execute_ipython> environment:\n'
    f'{_AGENT_SKILLS_DOCS}'
)

# ======= SYSTEM MESSAGE =======
MINIMAL_SYSTEM_PREFIX = """A chat between a curious user and an artificial intelligence assistant. The assistant gives helpful, detailed, and polite answers to the user's questions.
The assistant can interact with an interactive Python (Jupyter Notebook) environment and receive the corresponding output when needed. The code should be enclosed using "<execute_ipython>" tag, for example:
<execute_ipython>
print("Hello World!")
</execute_ipython>
The assistant can execute bash commands on behalf of the user by wrapping them with <execute_bash> and </execute_bash>.
For example, you can list the files in the current directory by <execute_bash> ls </execute_bash>.
"""

SYSTEM_PREFIX = MINIMAL_SYSTEM_PREFIX

SYSTEM_SUFFIX = """The assistant's response should be concise.
The assistant should include ONLY ONE <execute_ipython> or <execute_bash> in every one of the responses, unless the assistant is finished with the task or need more input or action from the user in order to proceed.
IMPORTANT: Whenever possible, execute the code for the user using <execute_ipython> or <execute_bash> instead of providing it.
"""

SWE_EXAMPLE = """
--- START OF EXAMPLE ---

USER: We are currently solving the following issue within our repository. Here is the issue text:
--- BEGIN ISSUE ---
TimeDelta serialization precision
Hi there!

I just found quite strange behaviour of `TimeDelta` field serialization

```python3
from marshmallow.fields import TimeDelta
from datetime import timedelta

td_field = TimeDelta(precision="milliseconds")

obj = dict()
obj["td_field"] = timedelta(milliseconds=345)

print(td_field.serialize("td_field", obj))
```

Output of this snippet is `344`, but it seems that `345` is correct.

Looks like a rounding issue here: https://github.com/marshmallow-code/marshmallow/blob/dev/src/marshmallow/fields.py#L1474
--- END ISSUE ---

[Current directory: /workspace/marshmallow-code__marshmallow]

ASSISTANT:
Let's first start by reproducing the results of the issue. The issue includes some example code for reproduction, which we can use. We'll create a new file called `reproduce.py` and paste the example code into it.
<execute_ipython>
create_file('reproduce.py')
</execute_ipython>

USER:
OBSERVATION:
[File: /workspace/marshmallow-code__marshmallow/reproduce.py (1 lines total)]
1|
[File /workspace/marshmallow-code__marshmallow/reproduce.py created.]

ASSISTANT:
Now let's paste in the example code from the issue.
<execute_ipython>
EDITED_CODE = \"\"\"from marshmallow.fields import TimeDelta
from datetime import timedelta

td_field = TimeDelta(precision="milliseconds")

obj = dict()
obj["td_field"] = timedelta(milliseconds=345)

print(td_field.serialize("td_field", obj))
\"\"\"
append_file(file_name='reproduce.py', content=EDITED_CODE)
</execute_ipython>

USER:
OBSERVATION:
[File: /workspace/marshmallow-code__marshmallow/reproduce.py (9 lines total)]
1|from marshmallow.fields import TimeDelta
2|from datetime import timedelta
3|
4|td_field = TimeDelta(precision="milliseconds")
5|
6|obj = dict()
7|obj["td_field"] = timedelta(milliseconds=345)
8|
9|print(td_field.serialize("td_field", obj))
[File updated. Please review the changes and make sure they are correct (correct indentation, no duplicate lines, etc). Edit the file again if necessary.]

ASSISTANT:
Now let's run the code to see if we see the same output as the issue.
<execute_bash>
python reproduce.py
</execute_bash>

USER:
OBSERVATION:
344

ASSISTANT:
We are indeed seeing the same output as the issue. The issue suggests that we should look at line 1474 of the `fields.py` file to see if there is a rounding issue. Let's open the `fields.py` file and navigate to line 1474 to see the relevant code. First we should find the `fields.py` file in the repository. It is likely to be in the `src/marshmallow` directory, but we should check to be sure.
<execute_bash>
ls -F
</execute_bash>

USER:
OBSERVATION:
AUTHORS.rst
CHANGELOG.rst
CODE_OF_CONDUCT.md
CONTRIBUTING.rst
LICENSE
MANIFEST.in
NOTICE
README.rst
RELEASING.md
azure-pipelines.yml
docs/
examples/
performance/
pyproject.toml
reproduce.py
setup.cfg
setup.py
src/
tests/
tox.ini

ASSISTANT:
It looks like the `src` directory is present, which suggests that the `fields.py` file is likely to be in the `src` directory. Let's use find_file to see where it is.
<execute_ipython>
find_file("fields.py", "/workspace/marshmallow-code__marshmallow/src")
</execute_ipython>

USER:
OBSERVATION:
[Found 1 matches for "fields.py" in /workspace/marshmallow-code__marshmallow/src]
/workspace/marshmallow-code__marshmallow/src/marshmallow/fields.py

ASSISTANT:
It looks like the `fields.py` file is present in the `./src/marshmallow/` directory. The issue also points to a specific URL with line number 1474. We should navigate to that line in fields.py to see the relevant code for the `TimeDelta` serialization.
<execute_ipython>
open_file(path="/workspace/marshmallow-code__marshmallow/src/marshmallow/fields.py", line_number=1474)
</execute_ipython>

USER:
OBSERVATION:
[File: /workspace/marshmallow-code__marshmallow/src/marshmallow/fields.py (1997 lines total)]
(1458 more lines above)
1459|            self.WEEKS,
1460|        )
1461|
1462|        if precision not in units:
1463|            msg = 'The precision must be {} or "{}".'.format(
1464|                ", ".join([f'"{each}"' for each in units[:-1]]), units[-1]
1465|            )
1466|            raise ValueError(msg)
1467|
1468|        self.precision = precision
1469|        super().__init__(**kwargs)
1470|
1471|    def _serialize(self, value, attr, obj, **kwargs):
1472|        if value is None:
1473|            return None
1474|        base_unit = dt.timedelta(**{self.precision: 1})
1475|        return int(value.total_seconds() / base_unit.total_seconds())
1476|
1477|    def _deserialize(self, value, attr, data, **kwargs):
1478|        try:
1479|            value = int(value)
1480|        except (TypeError, ValueError) as error:
1481|            raise self.make_error("invalid") from error
1482|
1483|        kwargs = {self.precision: value}
1484|
1485|        try:
1486|            return dt.timedelta(**kwargs)
1487|        except OverflowError as error:
1488|            raise self.make_error("invalid") from error
1489|
1490|
1491|class Mapping(Field):
1492|    \"\"\"An abstract class for objects with key-value pairs.
1493|
1494|    :param keys: A field class or instance for dict keys.
1495|    :param values: A field class or instance for dict values.
1496|    :param kwargs: The same keyword arguments that :class:`Field` receives.
1497|
1498|    .. note::
1499|        When the structure of nested data is not known, you may omit the
1500|        `keys` and `values` arguments to prevent content validation.
1501|
1502|    .. versionadded:: 3.0.0rc4
1503|    \"\"\"
1504|
1505|    mapping_type = dict
1506|
1507|    #: Default error messages.
1508|    default_error_messages = {"invalid": "Not a valid mapping type."}
1509|
1510|    def __init__(
1511|        self,
1512|        keys: typing.Optional[typing.Union[Field, type]] = None,
1513|        values: typing.Optional[typing.Union[Field, type]] = None,
1514|        **kwargs,
1515|    ):
1516|        super().__init__(**kwargs)
1517|        if keys is None:
1518|            self.key_field = None
1519|        else:
1520|            try:
1521|                self.key_field = resolve_field_instance(keys)
1522|            except FieldInstanceResolutionError as error:
1523|                raise ValueError(
1524|                    '"keys" must be a subclass or instance of '
1525|                    "marshmallow.base.FieldABC."
1526|                ) from error
1527|
1528|        if values is None:
1529|            self.value_field = None
1530|        else:
1531|            try:
1532|                self.value_field = resolve_field_instance(values)
1533|            except FieldInstanceResolutionError as error:
1534|                raise ValueError(
1535|                    '"values" must be a subclass or instance of '
1536|                    "marshmallow.base.FieldABC."
1537|                ) from error
1538|            if isinstance(self.value_field, Nested):
1539|                self.only = self.value_field.only
1540|                self.exclude = self.value_field.exclude
1541|
1542|    def _bind_to_schema(self, field_name, schema):
1543|        super()._bind_to_schema(field_name, schema)
1544|        if self.value_field:
1545|            self.value_field = copy.deepcopy(self.value_field)
1546|            self.value_field._bind_to_schema(field_name, self)
1547|        if isinstance(self.value_field, Nested):
1548|            self.value_field.only = self.only
1549|            self.value_field.exclude = self.exclude
1550|        if self.key_field:
1551|            self.key_field = copy.deepcopy(self.key_field)
1552|            self.key_field._bind_to_schema(field_name, self)
1553|
1554|    def _serialize(self, value, attr, obj, **kwargs):
1555|        if value is None:
1556|            return None
1557|        if not self.value_field and not self.key_field:
1558|            return self.mapping_type(value)
(439 more lines below)

ASSISTANT:
We are now looking at the relevant section of the `fields.py` file where the `TimeDelta` serialization occurs. The issue suggests that there is a rounding problem near line 1474. The current implementation uses integer division, which truncates the decimal part and can lead to incorrect rounding on line 1475. To fix this issue, we should ensure that the division results in a float, and then round the result to the nearest integer before converting it to an int. This should preserve the milliseconds precision as expected. Let's make the necessary edit to the code.
<execute_ipython>
insert_content_at_line(file_name='src/marshmallow/fields.py', line_number=1475, content="return int(round(value.total_seconds() / base_unit.total_seconds()))  # round to nearest int")
</execute_ipython>

USER:
OBSERVATION:
[Your proposed edit has introduced new syntax error(s). Please understand the errors and retry your edit command.]

ERRORS:
- E999 IndentationError: unexpected indent

[This is how your edit would have looked if applied]
-------------------------------------------------
[File: /marshmallow-code__marshmallow/src/marshmallow/fields.py (1997 lines total)]
(1468 more lines above)
1469|        super().__init__(**kwargs)
1470|
1471|    def _serialize(self, value, attr, obj, **kwargs):
1472|        if value is None:
1473|            return None
1474|        base_unit = dt.timedelta(**{self.precision: 1})
1475|return int(round(value.total_seconds() / base_unit.total_seconds()))  # round to nearest int
1476|
1477|    def _deserialize(self, value, attr, data, **kwargs):
1478|        try:
1479|            value = int(value)
(518 more lines below)
-------------------------------------------------

[This is the original code before your edit]
-------------------------------------------------
[File: /marshmallow-code__marshmallow/src/marshmallow/fields.py (1997 lines total)]
(1469 more lines above)
1470|
1471|    def _serialize(self, value, attr, obj, **kwargs):
1472|        if value is None:
1473|            return None
1474|        base_unit = dt.timedelta(**{self.precision: 1})
1475|        return int(value.total_seconds() / base_unit.total_seconds())
1476|
1477|    def _deserialize(self, value, attr, data, **kwargs):
1478|        try:
1479|            value = int(value)
1480|        except (TypeError, ValueError) as error:
(517 more lines below)
-------------------------------------------------
Your changes have NOT been applied. Please fix your edit command and try again.
You either need to 1) Specify the correct start/end line arguments or 2) Correct your edit code.
DO NOT re-run the same failed edit command. Running it again will lead to the same error.

ASSISTANT:
My edit command did not use the proper indentation, I will fix my syntax in this follow up edit command.
<execute_ipython>
EDITED_CODE="        return int(round(value.total_seconds() / base_unit.total_seconds()))  # round to nearest int"
insert_content_at_line(file_name='src/marshmallow/fields.py', line_number=1475, content=EDITED_CODE)
</execute_ipython>

USER:
OBSERVATION:
[File: /marshmallow-code__marshmallow/src/marshmallow/fields.py (1997 lines total)]
(1424 more lines above)
1425|
1426|    :param precision: Influences how the integer is interpreted during
1427|        (de)serialization. Must be 'days', 'seconds', 'microseconds',
1428|        'milliseconds', 'minutes', 'hours' or 'weeks'.
1429|    :param kwargs: The same keyword arguments that :class:`Field` receives.
1430|
1431|    .. versionchanged:: 2.0.0
1432|        Always serializes to an integer value to avoid rounding errors.
1433|        Add `precision` parameter.
1434|    \"\"\"
1435|
1436|    DAYS = "days"
1437|    SECONDS = "seconds"
1438|    MICROSECONDS = "microseconds"
1439|    MILLISECONDS = "milliseconds"
1440|    MINUTES = "minutes"
1441|    HOURS = "hours"
1442|    WEEKS = "weeks"
1443|
1444|    #: Default error messages.
1445|    default_error_messages = {
1446|        "invalid": "Not a valid period of time.",
1447|        "format": "{input!r} cannot be formatted as a timedelta.",
1448|    }
1449|
1450|    def __init__(self, precision: str = SECONDS, **kwargs):
1451|        precision = precision.lower()
1452|        units = (
1453|            self.DAYS,
1454|            self.SECONDS,
1455|            self.MICROSECONDS,
1456|            self.MILLISECONDS,
1457|            self.MINUTES,
1458|            self.HOURS,
1459|            self.WEEKS,
1460|        )
1461|
1462|        if precision not in units:
1463|            msg = 'The precision must be {} or "{}".'.format(
1464|                ", ".join([f'"{each}"' for each in units[:-1]]), units[-1]
1465|            )
1466|            raise ValueError(msg)
1467|
1468|        self.precision = precision
1469|        super().__init__(**kwargs)
1470|
1471|    def _serialize(self, value, attr, obj, **kwargs):
1472|        if value is None:
1473|            return None
1474|        base_unit = dt.timedelta(**{self.precision: 1})
1475|        return int(round(value.total_seconds() / base_unit.total_seconds()))  # round to nearest int
1476|
1477|    def _deserialize(self, value, attr, data, **kwargs):
1478|        try:
1479|            value = int(value)
1480|        except (TypeError, ValueError) as error:
1481|            raise self.make_error("invalid") from error
1482|
1483|        kwargs = {self.precision: value}
1484|
1485|        try:
1486|            return dt.timedelta(**kwargs)
1487|        except OverflowError as error:
1488|            raise self.make_error("invalid") from error
1489|
1490|
1491|class Mapping(Field):
1492|    \"\"\"An abstract class for objects with key-value pairs.
1493|
1494|    :param keys: A field class or instance for dict keys.
1495|    :param values: A field class or instance for dict values.
1496|    :param kwargs: The same keyword arguments that :class:`Field` receives.
1497|
1498|    .. note::
1499|        When the structure of nested data is not known, you may omit the
1500|        `keys` and `values` arguments to prevent content validation.
1501|
1502|    .. versionadded:: 3.0.0rc4
1503|    \"\"\"
1504|
1505|    mapping_type = dict
1506|
1507|    #: Default error messages.
1508|    default_error_messages = {"invalid": "Not a valid mapping type."}
1509|
1510|    def __init__(
1511|        self,
1512|        keys: typing.Optional[typing.Union[Field, type]] = None,
1513|        values: typing.Optional[typing.Union[Field, type]] = None,
1514|        **kwargs,
1515|    ):
1516|        super().__init__(**kwargs)
1517|        if keys is None:
1518|            self.key_field = None
1519|        else:
1520|            try:
1521|                self.key_field = resolve_field_instance(keys)
1522|            except FieldInstanceResolutionError as error:
1523|                raise ValueError(
1524|                    '"keys" must be a subclass or instance of '
(473 more lines below)
[File updated. Please review the changes and make sure they are correct (correct indentation, no duplicate lines, etc). Edit the file again if necessary.]

ASSISTANT:
The code has been updated to use the `round` function, which should fix the rounding issue. Before submitting the changes, it would be prudent to run the reproduce.py code again to ensure that this change has the desired effect. I see that "Current directory" is still `/marshmallow-code__marshmallow`, so we can just run `reproduce.py` directly.
<execute_bash>
python reproduce.py
</execute_bash>

USER:
OBSERVATION:
345

ASSISTANT:
The output has changed from 344 to 345, which suggests that the rounding issue has been fixed. Let's remove the reproduce.py file since it is no longer needed.
<execute_bash>
rm reproduce.py
</execute_bash>

USER:
OBSERVATION:

ASSISTANT:
rm doesn't have any output when it deletes successfully, so that must have worked. Now that we have fixed the issue, we can exit the current task.
<execute_bash>
exit
</execute_bash>

--- END OF EXAMPLE ---
"""

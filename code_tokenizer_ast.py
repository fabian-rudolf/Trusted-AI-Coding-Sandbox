import ast
import re
import hashlib
from typing import Dict, Tuple

# Modified Anonymization Script
class TokenCollector(ast.NodeVisitor):
    def __init__(self):
        super().__init__()
        self.identifiers = set()
        self.string_literals = set()

    def visit_Name(self, node):
        self.identifiers.add(node.id)

    def visit_Str(self, node):
        self.string_literals.add(repr(node.s))

    def visit_ClassDef(self, node):
        self.identifiers.add(node.name)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.identifiers.add(node.name)
        self.generic_visit(node)

    def visit_Assign(self, node):
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.identifiers.add(target.id)
        self.generic_visit(node)

def hash_string(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()

def tokenize(code: str) -> Tuple[Dict[str, str], str]:
    collector = TokenCollector()
    try:
        collector.visit(ast.parse(code))
    except Exception as e:
        print("Could not parse", e)
        return code

    sorted_identifiers = sorted(collector.identifiers)
    sorted_string_literals = sorted(collector.string_literals)

    anonymization_dict = {}
    detokenization_dict = {}

    for idx, identifier in enumerate(sorted_identifiers, start=1):
        anonymized_identifier = f'code_part_id_{idx}'
        anonymization_dict[identifier] = anonymized_identifier
        detokenization_dict[anonymized_identifier] = identifier

    anonymized_code = code
    for identifier, anon_identifier in anonymization_dict.items():
        anonymized_code = re.sub(r'\b' + re.escape(identifier) + r'\b', anon_identifier, anonymized_code)

    for string_literal in sorted_string_literals:
        literal_string = ast.literal_eval(string_literal)
        hashed_string = hash_string(literal_string)
        anonymized_code = anonymized_code.replace(string_literal, f"'{hashed_string}'")
        anonymization_dict[literal_string] = hashed_string
        detokenization_dict[hashed_string] = literal_string

    return detokenization_dict, anonymized_code

def detokenize(detokenization_dict: Dict[str, str], anonymized_code: str) -> str:
    restored_code = anonymized_code
    for anon_token, original in detokenization_dict.items():
        if anon_token.startswith('code_part_id_'):
            restored_code = re.sub(r'\b' + re.escape(anon_token) + r'\b', original, restored_code)
        else:
            restored_code = restored_code.replace(f"'{anon_token}'", original)

    return restored_code

class TestTokenizer():
    def __init__(self):
        public_method_names = [method for method in dir(self) if callable(getattr(self, method)) if not method.startswith('_')]  # 'private' methods start from _
        for method in public_method_names:
            getattr(self, method)()  # call

    @staticmethod
    def __assert_equals(expected_anonymized_code, anonymized_code, verbose=True):
        # Normalize newlines for comparison
        expected_lines = expected_anonymized_code.strip().split('\\n')
        actual_lines = anonymized_code.strip().split('\\n')

        assert actual_lines == expected_lines, f"ACTUAL\n\n\n{anonymized_code.strip()} \n\n does not equal EXPECTED\n\n\n {expected_anonymized_code.strip()}"

        if verbose:
            print(f"Passed test case: actual\n\n\n{anonymized_code.strip()} \n\n equals expected\n\n\n {expected_anonymized_code.strip()}")


    def test_basic_identifiers(self):
        code = """
class MyClass:
    def my_method(self, param):
        return param

def add(a, b):
    return a + b

my_variable = 10
        """
        expected_anonymized_code = """
class code_part_id_1:
    def code_part_id_5(self, code_part_id_7):
        return code_part_id_7

def code_part_id_3(code_part_id_2, code_part_id_4):
    return code_part_id_2 + code_part_id_4

code_part_id_6 = 10
        """
        _, anonymized_code = tokenize(code)
        self.__assert_equals(expected_anonymized_code, anonymized_code)

    def test_strings_and_fstrings(self):
        code = "my_string = 'This is a string containing MyClass and add'\n"
        expected_anonymized_code = "code_part_id_1 = 'e89dfaeffe1c93041ab810ecf73be5f8be64f926fc4a835236d23cd738eb9393'\n"
        _, anonymized_code = tokenize(code)
        self.__assert_equals(expected_anonymized_code, anonymized_code)

    def test_multiline_byte_raw_strings(self):
        # Test case
        code = """
multiline_string = '''This is a\\nmultiline string with\\nMyClass'''
raw_string = r'Raw string with add'
byte_string = b'Byte string with MyClass'
        """
        _, anonymized_code = tokenize(code)

        expected_anonymized_code = """
code_part_id_2 = '''af038aaaf625fe9f2d0cd3f0938dec464b72ef3ab02e424bbd8541e670e84e7d'''
code_part_id_3 = r'a9c4320a1d60737eac6f7585b806f87d67950a47a834b9c5c979fb8a3c70db4a'
code_part_id_1 = b'Byte string with MyClass'
        """

        self.__assert_equals(expected_anonymized_code, anonymized_code)

    def test_pii_and_secret_names(self):
        code = """
social_security_number = '123-45-6789'
internal_code_name = 'ProjectX'
        """
        expected_anonymized_code = """
code_part_id_2 = '01a54629efb952287e554eb23ef69c52097a75aecc0e3a93ca0855ab6d7a31a0'
code_part_id_1 = '41838ca025380b5cdf10129acd993ccf5ae477c3b410f7f98fb9769dc4b6a5ba'
        """
        _, anonymized_code = tokenize(code)
        self.__assert_equals(expected_anonymized_code, anonymized_code)

# Run the tests
if __name__ == '__main__':
    TestTokenizer()

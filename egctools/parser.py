import textformats
import importlib.resources
_data = importlib.resources.files("egctools").joinpath("data")
_egcspec = _data.joinpath("egc-spec")
_specfile = _egcspec.joinpath("egc.tf.yaml")
SPEC = textformats.Specification(str(_specfile))

def parsed_line(s):
  elements = SPEC["line"].decode(s.rstrip("\n"))
  return elements

def encode_line(data):
  return SPEC["line"].encode(data)

def parsed_lines(fname):
  for line in open(fname):
    yield parsed_line(line)

def unparsed_and_parsed_lines(fname):
  for line in open(fname):
    yield (line.rstrip("\n"), parsed_line(line))


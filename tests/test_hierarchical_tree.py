"""Tests for hierarchical label tree data structure and utilities."""
import pytest
import tempfile
import textwrap

from tater.widgets.hierarchical_label import (
    Node, build_tree, _build_tree, _find_path, _node_at,
    load_hierarchy_from_yaml,
)


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class TestNode:
    def test_leaf_node(self):
        n = Node("a")
        assert n.is_leaf is True

    def test_non_leaf_node(self):
        n = Node("a", [Node("b")])
        assert n.is_leaf is False

    def test_find_present(self):
        child = Node("b")
        n = Node("a", [child, Node("c")])
        assert n.find("b") is child

    def test_find_missing(self):
        n = Node("a", [Node("b")])
        assert n.find("x") is None

    def test_find_does_not_recurse(self):
        # find() only checks direct children
        n = Node("a", [Node("b", [Node("c")])])
        assert n.find("c") is None

    def test_all_leaves_leaf(self):
        n = Node("a")
        assert [x.name for x in n.all_leaves()] == ["a"]

    def test_all_leaves_tree(self):
        tree = Node("root", [
            Node("A", [Node("A1"), Node("A2")]),
            Node("B"),
        ])
        assert {x.name for x in tree.all_leaves()} == {"A1", "A2", "B"}

    def test_all_nodes_bfs_order(self):
        tree = Node("root", [
            Node("A", [Node("A1")]),
            Node("B"),
        ])
        names = [n.name for n in tree.all_nodes()]
        assert names[0] == "root"
        # BFS: root, A, B, A1
        assert set(names) == {"root", "A", "B", "A1"}
        assert names.index("A") < names.index("A1")
        assert names.index("B") < names.index("A1")

    def test_all_nodes_includes_root(self):
        tree = Node("root", [Node("child")])
        names = [n.name for n in tree.all_nodes()]
        assert "root" in names


# ---------------------------------------------------------------------------
# build_tree / _build_tree
# ---------------------------------------------------------------------------

class TestBuildTree:
    def test_flat_list(self):
        root = build_tree(["cat", "dog", "fish"])
        assert root.name == "__root__"
        assert [c.name for c in root.children] == ["cat", "dog", "fish"]
        assert all(c.is_leaf for c in root.children)

    def test_single_key_dict_uses_key_as_root(self):
        root = build_tree({"Animals": ["cat", "dog"]})
        assert root.name == "Animals"
        assert [c.name for c in root.children] == ["cat", "dog"]

    def test_multi_key_dict_creates_virtual_root(self):
        root = build_tree({"A": ["a1"], "B": ["b1"]})
        assert root.name == "__root__"
        assert {c.name for c in root.children} == {"A", "B"}

    def test_nested_dict(self):
        root = build_tree({"Animals": {"Mammals": ["dog", "cat"], "Birds": ["parrot"]}})
        mammals = root.find("Mammals")
        assert mammals is not None
        assert {c.name for c in mammals.children} == {"dog", "cat"}

    def test_list_of_dicts(self):
        root = build_tree(["simple", {"nested": ["n1", "n2"]}])
        assert root.find("simple").is_leaf
        nested = root.find("nested")
        assert nested is not None
        assert [c.name for c in nested.children] == ["n1", "n2"]

    def test_empty_dict_leaf(self):
        root = _build_tree("x", {})
        assert root.is_leaf

    def test_none_leaf(self):
        root = _build_tree("x", None)
        assert root.is_leaf

    def test_scalar_value(self):
        # Scalar data becomes the node name (not children)
        root = _build_tree("ignored", 42)
        assert root.name == "42"

    def test_raises_on_wrong_type(self):
        with pytest.raises(TypeError):
            build_tree("not a dict or list")


# ---------------------------------------------------------------------------
# _find_path
# ---------------------------------------------------------------------------

class TestFindPath:
    @pytest.fixture
    def tree(self):
        return build_tree({
            "Animals": {
                "Mammals": ["dog", "cat"],
                "Birds": ["parrot", "eagle"],
            },
            "Plants": ["rose", "oak"],
        })

    def test_finds_leaf(self, tree):
        assert _find_path(tree, "dog") == ["Animals", "Mammals", "dog"]

    def test_finds_intermediate(self, tree):
        assert _find_path(tree, "Mammals") == ["Animals", "Mammals"]

    def test_finds_top_level(self, tree):
        assert _find_path(tree, "Animals") == ["Animals"]

    def test_missing_returns_empty(self, tree):
        assert _find_path(tree, "unicorn") == []

    def test_does_not_find_root(self, tree):
        # root itself is not returned
        assert _find_path(tree, tree.name) == []

    def test_single_level(self):
        root = build_tree(["a", "b", "c"])
        assert _find_path(root, "b") == ["b"]


# ---------------------------------------------------------------------------
# _node_at
# ---------------------------------------------------------------------------

class TestNodeAt:
    @pytest.fixture
    def tree(self):
        return build_tree({"A": {"B": ["C", "D"]}, "E": []})

    def test_empty_path_returns_root(self, tree):
        assert _node_at(tree, []) is tree

    def test_single_step(self, tree):
        node = _node_at(tree, ["A"])
        assert node.name == "A"

    def test_multi_step(self, tree):
        node = _node_at(tree, ["A", "B", "C"])
        assert node.name == "C"

    def test_missing_step_returns_root(self, tree):
        # Falls back to root on a bad path segment
        node = _node_at(tree, ["A", "X"])
        assert node is tree

    def test_partial_bad_path_returns_root(self, tree):
        node = _node_at(tree, ["nonexistent"])
        assert node is tree


# ---------------------------------------------------------------------------
# load_hierarchy_from_yaml
# ---------------------------------------------------------------------------

class TestLoadHierarchyFromYaml:
    def test_basic_yaml(self, tmp_path):
        yaml_file = tmp_path / "ontology.yaml"
        yaml_file.write_text(textwrap.dedent("""\
            Animals:
              Mammals:
                - dog
                - cat
              Birds:
                - parrot
            Plants:
              - rose
        """))
        root = load_hierarchy_from_yaml(yaml_file)
        assert root.name == "__root__"
        animals = root.find("Animals")
        assert animals is not None
        mammals = animals.find("Mammals")
        assert mammals is not None
        assert {c.name for c in mammals.children} == {"dog", "cat"}

    def test_single_root_yaml(self, tmp_path):
        yaml_file = tmp_path / "single.yaml"
        yaml_file.write_text(textwrap.dedent("""\
            Breeds:
              - labrador
              - poodle
        """))
        root = load_hierarchy_from_yaml(yaml_file)
        assert root.name == "Breeds"
        assert {c.name for c in root.children} == {"labrador", "poodle"}

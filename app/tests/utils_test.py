from app.helpers.utils import merge_dicts


def test_merge_dicts():
    """
    Test different types of key value pair getting merged
    """
    dict1 = {
        "unique_key_dict1": 10,
        "override_key": 11,
        "array_key": [12, 13, 14],
        "dict_key": {"unique_key2_dict1": 15},
    }
    dict2 = {
        "unique_key_dict2": 20,
        "override_key": 21,
        "array_key": [22, 23, 24],
        "dict_key": {"unique_key2_dict2": 25},
    }
    merge_dicts(dict1, dict2)
    assert dict1 == {
        "unique_key_dict1": 10,
        "unique_key_dict2": 20,
        "override_key": 21,
        "array_key": [22, 23, 24],
        "dict_key": {"unique_key2_dict1": 15, "unique_key2_dict2": 25},
    }


def test_merge_dicts_append_lists():
    """
    Tests merging with append_lists set to True
    """
    dict1 = {"array_key": [12, 13, 14]}
    dict2 = {"array_key": [22, 23, 24]}
    merge_dicts(dict1, dict2, append_lists=True)
    assert dict1 == {"array_key": [12, 13, 14, 22, 23, 24]}

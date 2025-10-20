#!/usr/bin/env python3
"""Test script for AstrbotInjector"""

import os
import sys

# Add the module path
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "astrbot_modules", "astrbot_canary_api", "src"
    ),
)

from astrbot_canary_api.decorators import AstrbotInjector


def test_global_injection():
    """Test global dependency injection"""
    print("Testing global injection...")

    # Set global dependencies
    AstrbotInjector.set("db", "global_db_instance")
    AstrbotInjector.set("config", "global_config_instance")

    @AstrbotInjector
    def my_function(db, config, extra="default"):
        return f"db={db}, config={config}, extra={extra}"

    # Call function
    result = my_function(extra="test")
    expected = "db=global_db_instance, config=global_config_instance, extra=test"
    assert result == expected, f"Expected {expected}, got {result}"
    print("Global injection test passed!")


def test_local_injection():
    """Test local dependency injection"""
    print("Testing local injection...")

    # Create local injector
    local_injector = AstrbotInjector("test_injector")
    local_injector.set_local("db", "local_db_instance")
    local_injector.set_local("config", "local_config_instance")

    @local_injector
    def my_function(db, config, extra="default"):
        return f"db={db}, config={config}, extra={extra}"

    # Call function
    result = my_function(extra="test")
    expected = "db=local_db_instance, config=local_config_instance, extra=test"
    assert result == expected, f"Expected {expected}, got {result}"
    print("Local injection test passed!")


def test_priority():
    """Test that local dependencies override global"""
    print("Testing priority (local over global)...")

    # Set global
    AstrbotInjector.set("db", "global_db")
    AstrbotInjector.set("config", "global_config")

    # Create local with override
    local_injector = AstrbotInjector("priority_test")
    local_injector.set_local("db", "local_db_override")

    @local_injector
    def my_function(db, config):
        return f"db={db}, config={config}"

    result = my_function()
    expected = "db=local_db_override, config=global_config"
    assert result == expected, f"Expected {expected}, got {result}"
    print("Priority test passed!")


def test_not_callable():
    """Test that non-callable instance raises error"""
    print("Testing non-callable instance...")

    local_injector = AstrbotInjector("not_callable")
    try:
        local_injector()
        assert False, "Should have raised TypeError"
    except TypeError as e:
        assert "not callable" in str(e)
        print("Non-callable test passed!")


if __name__ == "__main__":
    test_global_injection()
    test_local_injection()
    test_priority()
    test_not_callable()
    print("All tests passed!")

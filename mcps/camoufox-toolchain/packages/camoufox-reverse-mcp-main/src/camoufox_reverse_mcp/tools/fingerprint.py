# 模块说明: 兼容保留模块,提示旧指纹工具已迁移到其他工具实现。
# fingerprint.py - v0.9.0: tools moved/removed
#
# get_fingerprint_info -> use evaluate_js or compare_env
# check_detection -> use navigate + take_screenshot manually
# bypass_debugger_trap -> use inject_hook_preset("debugger_bypass")
#
# This module is kept empty to avoid import errors from server.py.
# compare_env is now in jsvmp.py.

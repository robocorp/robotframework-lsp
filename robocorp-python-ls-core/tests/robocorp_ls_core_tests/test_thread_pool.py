def test_thread_pool():
    from robocorp_ls_core.jsonrpc.thread_pool import obtain_thread_pool
    from robocorp_ls_core.jsonrpc.thread_pool import dispose_thread_pool

    tp = obtain_thread_pool()
    assert tp is not None
    assert obtain_thread_pool() is tp
    dispose_thread_pool()
    assert tp._shutdown
    assert obtain_thread_pool() is not tp
    dispose_thread_pool()

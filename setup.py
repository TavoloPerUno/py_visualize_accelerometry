"""Panel server setup script — registers custom Tornado handlers."""

from visualize_accelerometry.admin import AdminHandler


def setup(port, address, app_paths):
    """Called by panel serve --setup."""
    from tornado.web import Application
    import panel as pn

    # Schedule handler registration after the server starts
    def _add_handlers():
        tornado_app = pn.state._server._tornado
        tornado_app.add_handlers(".*", [("/admin", AdminHandler)])
        print("[setup] Admin handler registered at /admin")

    pn.state.execute(_add_handlers)

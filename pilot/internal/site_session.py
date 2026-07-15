def create_administrator_session() -> str:
    import frappe
    from frappe.auth import CookieManager, LoginManager

    frappe.utils.set_request(path="/")
    frappe.local.cookie_manager = CookieManager()
    frappe.local.login_manager = LoginManager()
    frappe.local.login_manager.login_as("Administrator")
    return frappe.session.sid

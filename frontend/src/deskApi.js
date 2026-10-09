// Reuse the authenticated Frappe Desk transport. frappe.call handles session
// cookies, CSRF validation and API error responses on both light/dark Desk.
export function deskCall(method, args = {}) {
	return new Promise((resolve, reject) => {
		const frappe = window.frappe;
		if (typeof frappe?.call !== "function") {
			reject(new Error("Frappe Desk is unavailable. Reload the page."));
			return;
		}
		try {
			frappe.call({
				method,
				args,
				callback(response) {
					if (response?.exc) {
						reject(new Error(response.exception || "Frappe request failed"));
						return;
					}
					resolve(response?.message);
				},
				error(error) {
					reject(error instanceof Error ? error : new Error(error?.message || error?.responseJSON?.exception || "Frappe request failed"));
				},
			});
		} catch (error) {
			reject(error);
		}
	});
}

// frappe-ui createResource passes an object containing url and params.
// Return the unwrapped message as frappe-ui's resource transform expects.
export function deskResourceFetcher({ url, params = {} }) {
	return deskCall(url, params);
}

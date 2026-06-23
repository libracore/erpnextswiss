// Guards Frappe's desk sidebar menu against iconless navbar entries.
(function () {
	function can_render(item) {
		if (!item) {
			return false;
		}
		if (!item.condition) {
			return true;
		}
		try {
			return typeof item.condition === "function"
				? item.condition()
				: frappe.utils.eval(item.condition);
		} catch (error) {
			console.warn("Skipped sidebar menu item with invalid condition", item, error);
			return false;
		}
	}

	function route_to(url) {
		if (!url) {
			return;
		}
		if (url.startsWith("/desk")) {
			frappe.set_route(url);
		} else if (url.startsWith("/")) {
			window.location.href = window.location.origin + url;
		} else {
			window.open(url, "_blank").focus();
		}
	}

	function add_icon($target, item) {
		if (item.icon) {
			$target.html(frappe.utils.icon(item.icon));
			return;
		}
		if (item.icon_url) {
			$("<img>").addClass("logo").attr("src", item.icon_url).appendTo($target);
			return;
		}
		if (item.icon_html) {
			$target.html(item.icon_html);
			return;
		}
		$target.html(frappe.utils.icon("circle"));
	}

	function patch_sidebar_header() {
		if (!window.frappe || !frappe.ui || !frappe.ui.SidebarHeader) {
			return false;
		}

		const proto = frappe.ui.SidebarHeader.prototype;
		if (!proto || proto.__erpnextswiss_sidebar_safety_patched) {
			return true;
		}

		proto.add_app_item = function (item) {
			if (!can_render(item)) {
				return;
			}
			if (item.is_divider) {
				$('<div class="dropdown-divider documentation-links"></div>').appendTo(
					this.dropdown_menu
				);
				return;
			}
			if (!item.label) {
				return;
			}

			const item_name =
				item.name || item.label || (frappe.utils.get_random && frappe.utils.get_random(8));
			const $wrapper = $('<div class="dropdown-menu-item"></div>').attr("data-name", item_name);
			if (item.route) {
				$wrapper.attr("data-app-route", item.route);
			}

			const $link = $("<a></a>");
			if (item.href) {
				$link.attr("href", item.href);
			}

			const $icon = $('<div class="sidebar-item-icon"></div>');
			add_icon($icon, item);
			$link.append($icon);

			$("<span></span>").addClass("menu-item-title").text(__(item.label)).appendTo($link);

			if (item.shortcut) {
				$("<span></span>")
					.addClass("menu-item-shortcut")
					.text(frappe.ui.keys.get_shortcut_label(item.shortcut))
					.appendTo($link);
			}

			$wrapper.append($link).appendTo(this.dropdown_menu);
		};

		proto.setup_select_options = function () {
			this.dropdown_menu.find(".dropdown-menu-item").on("click", (event) => {
				const $item = $(event.delegateTarget);
				const name = $item.attr("data-name");
				const current_item = this.dropdown_items.find(
					(item) => item.name == name || item.label == name
				);

				if (!current_item) {
					return;
				}
				if (current_item.items && !current_item.onClick && !current_item.url && !current_item.action) {
					return;
				}

				this.dropdown_menu.toggleClass("hidden");
				this.toggle_active();

				if (current_item.onClick) {
					return current_item.onClick($item);
				}
				if (current_item.action) {
					return frappe.utils.eval(current_item.action);
				}
				if (current_item.url) {
					return route_to(current_item.url);
				}
				if (current_item.route) {
					return frappe.set_route(current_item.route);
				}
			});
		};

		proto.__erpnextswiss_sidebar_safety_patched = true;
		return true;
	}

	if (!patch_sidebar_header()) {
		if (window.frappe && frappe.ready) {
			frappe.ready(() => patch_sidebar_header());
		}
		const patch_interval = window.setInterval(() => {
			if (patch_sidebar_header()) {
				window.clearInterval(patch_interval);
			}
		}, 100);
		window.setTimeout(() => window.clearInterval(patch_interval), 5000);
	}
})();

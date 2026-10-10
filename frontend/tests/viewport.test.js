import { mount } from "@vue/test-utils";
import { nextTick, ref } from "vue";
import { describe, it, expect, vi, afterEach } from "vitest";
import { usePlannerViewport } from "../src/usePlannerViewport";

let wrapper;
afterEach(() => { wrapper?.unmount(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

it("fits the space below Desk's header, adapts on resize and page show, and cleans up", async () => {
	let top = 180;
	let observeCallback;
	const disconnect = vi.fn();
	vi.stubGlobal("ResizeObserver", class {
		constructor(callback) { observeCallback = callback; }
		observe() {}
		disconnect = disconnect;
	});
	vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(() => ({ top }));
	vi.spyOn(window, "innerHeight", "get").mockReturnValue(900);
	const remove = vi.spyOn(window, "removeEventListener");
	wrapper = mount({
		setup() { const element = ref(null); return { element, height: usePlannerViewport(element) }; },
		template: '<div ref="element" :style="{ height: height + \'px\' }"></div>',
	}, { attachTo: document.body });
	await nextTick();
	expect(wrapper.element.style.height).toBe("712px");
	vi.spyOn(window, "innerHeight", "get").mockReturnValue(600);
	window.dispatchEvent(new Event("resize"));
	await new Promise((resolve) => requestAnimationFrame(resolve));
	await nextTick();
	expect(wrapper.element.style.height).toBe("412px");
	top = 120;
	observeCallback();
	await new Promise((resolve) => requestAnimationFrame(resolve));
	await nextTick();
	expect(wrapper.element.style.height).toBe("472px");
	wrapper.unmount();
	wrapper = null;
	expect(disconnect).toHaveBeenCalled();
	expect(remove).toHaveBeenCalledWith("resize", expect.any(Function));
});

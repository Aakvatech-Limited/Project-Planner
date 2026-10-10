import { onMounted, onBeforeUnmount, ref } from "vue";

// Measure the space below Desk's real header instead of assuming a fixed
// navbar height. Re-measure when a hidden Desk page is shown or resized.
export function usePlannerViewport(element) {
	const height = ref(0);
	let observer;
	let frame;

	function measure() {
		if (!element.value) return;
		const viewport = window.visualViewport;
		const bottom = viewport ? viewport.height + viewport.offsetTop : window.innerHeight;
		const top = Math.max(0, element.value.getBoundingClientRect().top);
		height.value = Math.max(0, Math.floor(bottom - top - 8));
	}

	function scheduleMeasure() {
		cancelAnimationFrame(frame);
		frame = requestAnimationFrame(measure);
	}

	onMounted(() => {
		measure();
		scheduleMeasure();
		window.addEventListener("resize", scheduleMeasure);
		window.visualViewport?.addEventListener("resize", scheduleMeasure);
		if (typeof ResizeObserver !== "undefined" && element.value?.parentElement) {
			observer = new ResizeObserver(scheduleMeasure);
			observer.observe(element.value.parentElement);
		}
	});

	onBeforeUnmount(() => {
		cancelAnimationFrame(frame);
		observer?.disconnect();
		window.removeEventListener("resize", scheduleMeasure);
		window.visualViewport?.removeEventListener("resize", scheduleMeasure);
	});

	return height;
}

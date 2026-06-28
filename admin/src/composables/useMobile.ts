import { ref, onMounted, onUnmounted } from "vue";

export function useMobile(breakpoint = 768) {
  const width = ref(window.innerWidth);
  const isMobile = ref(window.innerWidth < breakpoint);

  function update() {
    width.value = window.innerWidth;
    isMobile.value = width.value < breakpoint;
  }

  onMounted(() => {
    window.addEventListener("resize", update);
  });

  onUnmounted(() => {
    window.removeEventListener("resize", update);
  });

  return { width, isMobile };
}

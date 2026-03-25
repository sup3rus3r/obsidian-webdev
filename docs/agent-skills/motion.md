# Motion (Framer Motion) Skill — Obsidian WebDev Agent

Use this skill for all animations, transitions, gestures, and motion design in React/Next.js projects.

---

## Package

```bash
npm install motion
```

> Import from `"motion/react"` — NOT `"framer-motion"` (that is the old package name).

---

## Core imports

```tsx
import { motion, AnimatePresence, useMotionValue, useTransform, useSpring, useAnimate, useInView, useScroll, stagger } from "motion/react"
```

---

## Basic animation

```tsx
// Fade in on mount
<motion.div
  initial={{ opacity: 0, y: 20 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.4, ease: "easeOut" }}
>
  content
</motion.div>
```

```tsx
// Scale on hover + tap
<motion.button
  whileHover={{ scale: 1.05 }}
  whileTap={{ scale: 0.95 }}
  transition={{ type: "spring", stiffness: 400, damping: 20 }}
>
  Click me
</motion.button>
```

---

## Transition types

```tsx
// Tween (CSS-like)
transition={{ duration: 0.3, ease: "easeInOut" }}
transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}  // custom cubic-bezier

// Spring (physics-based — prefer for interactive elements)
transition={{ type: "spring", stiffness: 300, damping: 25 }}
transition={{ type: "spring", bounce: 0.4, duration: 0.6 }}

// Delay / stagger
transition={{ delay: 0.2 }}
```

---

## Variants — for coordinated animations

```tsx
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,   // each child animates 100ms after the previous
      delayChildren: 0.2,
    },
  },
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } },
}

// Usage
<motion.ul variants={containerVariants} initial="hidden" animate="visible">
  {items.map(item => (
    <motion.li key={item.id} variants={itemVariants}>
      {item.name}
    </motion.li>
  ))}
</motion.ul>
```

---

## AnimatePresence — mount/unmount animations

```tsx
'use client'
import { AnimatePresence, motion } from "motion/react"

// Wrap conditional rendering — key is required
<AnimatePresence>
  {isVisible && (
    <motion.div
      key="modal"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.2 }}
    />
  )}
</AnimatePresence>

// List items — key each item so exit plays on removal
<AnimatePresence>
  {items.map(item => (
    <motion.div
      key={item.id}
      layout                              // animate layout changes automatically
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
    />
  ))}
</AnimatePresence>
```

---

## Layout animations

```tsx
// Animate any layout change automatically (position, size, reorder)
<motion.div layout>content</motion.div>

// Shared layout — elements with the same layoutId morph between states
<motion.div layoutId="hero-image" />  // in list
<motion.div layoutId="hero-image" />  // in modal — will animate between them
```

---

## Scroll animations

```tsx
'use client'
import { useScroll, useTransform, motion } from "motion/react"

// Parallax
function ParallaxSection() {
  const { scrollY } = useScroll()
  const y = useTransform(scrollY, [0, 500], [0, -150])
  return <motion.div style={{ y }}>content</motion.div>
}

// Animate when element enters viewport
import { useInView } from "motion/react"

function FadeInSection() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })
  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 40 }}
      animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.6, ease: "easeOut" }}
    />
  )
}
```

---

## Gestures

```tsx
// Drag
<motion.div
  drag
  dragConstraints={{ left: -100, right: 100, top: -100, bottom: 100 }}
  dragElastic={0.2}
  whileDrag={{ scale: 1.1 }}
/>

// Drag on one axis
<motion.div drag="x" dragSnapToOrigin />
```

---

## useAnimate — programmatic animations

```tsx
'use client'
import { useAnimate, stagger } from "motion/react"

function AnimatedList() {
  const [scope, animate] = useAnimate()

  async function handleClick() {
    await animate("li", { opacity: [0, 1], y: [20, 0] }, { delay: stagger(0.05) })
  }

  return (
    <ul ref={scope}>
      <li>Item 1</li>
      <li>Item 2</li>
    </ul>
  )
}
```

---

## Motion values — for performance-sensitive animations

```tsx
'use client'
import { useMotionValue, useTransform, useSpring, motion } from "motion/react"

function FollowCursor() {
  const x = useMotionValue(0)
  const y = useMotionValue(0)
  const rotateX = useTransform(y, [-100, 100], [15, -15])
  const rotateY = useTransform(x, [-100, 100], [-15, 15])

  // Smooth spring physics on a motion value
  const springX = useSpring(x, { stiffness: 150, damping: 20 })

  return (
    <motion.div
      style={{ x: springX, rotateX, rotateY }}
      onMouseMove={(e) => {
        x.set(e.clientX - window.innerWidth / 2)
        y.set(e.clientY - window.innerHeight / 2)
      }}
    />
  )
}
```

---

## Page transitions (Next.js App Router)

```tsx
// components/PageTransition.tsx
'use client'
import { motion, AnimatePresence } from "motion/react"

export function PageTransition({ children }: { children: React.ReactNode }) {
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={typeof window !== "undefined" ? window.location.pathname : "page"}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8 }}
        transition={{ duration: 0.25, ease: "easeInOut" }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  )
}
```

---

## Rules for beautiful animations

- **Spring > tween** for interactive elements (buttons, cards, modals)
- **Tween** for background/ambient effects (page fades, parallax)
- Keep `duration` under 400ms for UI feedback — longer feels sluggish
- Use `staggerChildren` to reveal lists — never animate all items at once
- Use `layout` prop whenever elements shift position (add/remove items, accordion)
- Use `layoutId` for shared element transitions (expand card to modal, tab indicator)
- Never use JS `setTimeout` for sequencing — use `transition.delay` or `stagger()`
- Always add `'use client'` — motion components are client-only

---

## What NOT to do

- Never import from `"framer-motion"` — use `"motion/react"`
- Never animate `width`/`height` directly — animate `scaleX`/`scaleY` or use `layout` prop (GPU-accelerated)
- Never use `display: none` to hide — use `AnimatePresence` + `exit` so the exit animation plays
- Never put `<AnimatePresence>` inside a `motion` element that also has `initial`/`animate` — keep them separate
- Never animate `top`/`left` — use `x`/`y` in `style` or `animate` (composited, no layout thrash)

---

## Context7 — fetch before using any API you are unsure about

```
GET https://context7.com/api/v1/framer/motion/docs?tokens=7000&topic=<TOPIC>
```

| What you need | Topic |
|---|---|
| Installation / setup | `introduction` |
| Basic animation props | `animation` |
| Variants and orchestration | `variants` |
| Mount/unmount transitions | `animate-presence` |
| Layout animations | `layout-animations` |
| Shared layout / layoutId | `shared-layout-animations` |
| Scroll animations | `scroll-animations` |
| Gestures (drag, hover, tap) | `gestures` |
| useAnimate / imperative API | `use-animate` |
| Motion values | `motion-values` |
| useScroll / useTransform | `use-scroll` |
| useInView | `use-in-view` |
| useSpring | `use-spring` |

**Call example:**
```
web_fetch("https://context7.com/api/v1/framer/motion/docs?tokens=7000&topic=variants")
```

Always fetch when:
- Using an API you haven't used in this project yet
- Unsure about prop names or option shapes
- Building complex orchestration (stagger, shared layout, scroll-linked)

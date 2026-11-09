// Exact critically damped spring: retargeting preserves position and velocity.
export function createSpring(initial: number[], update: (values: number[]) => void, response = .32) {
  let values = [...initial]
  let targets = [...initial]
  let velocities = initial.map(() => 0)
  let frame = 0
  let lastTime = 0
  const omega = 2 * Math.PI / response

  const tick = (time: number) => {
    const dt = Math.min((time - lastTime) / 1000, .064)
    lastTime = time
    const decay = Math.exp(-omega * dt)
    let moving = false
    values = values.map((value, index) => {
      const offset = value - targets[index]
      const coefficient = velocities[index] + omega * offset
      const next = targets[index] + (offset + coefficient * dt) * decay
      velocities[index] = (velocities[index] - omega * coefficient * dt) * decay
      if (Math.abs(next - targets[index]) > .0001 || Math.abs(velocities[index]) > .001) moving = true
      return next
    })
    update(values)
    if (moving) frame = requestAnimationFrame(tick)
    else { frame = 0; values = [...targets]; velocities.fill(0); update(values) }
  }

  return {
    get running() { return frame !== 0 },
    to(next: number[]) {
      targets = [...next]
      if (!frame) { lastTime = performance.now(); frame = requestAnimationFrame(tick) }
    },
    jump(next: number[]) {
      cancelAnimationFrame(frame); frame = 0
      values = [...next]; targets = [...next]; velocities = next.map(() => 0)
      update(values)
    },
    stop() { cancelAnimationFrame(frame); frame = 0 },
  }
}

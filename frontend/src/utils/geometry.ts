/** Shoelace 公式计算多边形面积 */
export function polygonArea(points: number[][]): number {
  if (points.length < 3) return 0
  const n = points.length
  let area = 0
  for (let i = 0; i < n; i++) {
    const j = (i + 1) % n
    area += points[i][1] * points[j][0]
    area -= points[j][1] * points[i][0]
  }
  return Math.abs(area) / 2
}

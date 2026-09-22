import { useEffect, useMemo, useRef, useState } from 'react'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'
import { Download } from 'lucide-react'

type ClinicalChartProps = {
  option: EChartsOption
  height?: number
  className?: string
  onEvents?: Record<string, (params: unknown) => void>
  exportTitle?: string
}

export function ClinicalChart({
  option,
  height = 280,
  className,
  onEvents,
  exportTitle,
}: ClinicalChartProps) {
  const [isDark, setIsDark] = useState(() => document.documentElement.dataset.theme === 'dark')
  const chartRef = useRef<ReactECharts>(null)

  useEffect(() => {
    const observer = new MutationObserver(() => {
      setIsDark(document.documentElement.dataset.theme === 'dark')
    })
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
    return () => observer.disconnect()
  }, [])

  const exportBackground = isDark ? '#0e233a' : '#ffffff'
  const exportOption = useMemo<EChartsOption>(() => ({
    ...option,
    backgroundColor: exportBackground,
  }), [exportBackground, option])

  function saveImage(dataUrl: string) {
    const link = document.createElement('a')
    link.href = dataUrl
    link.download = `${(exportTitle || 'lung-panel-chart').toLowerCase().replace(/[^a-z0-9]+/g, '-')}.png`
    link.click()
  }

  function downloadChart() {
    const chart = chartRef.current?.getEchartsInstance()
    if (!chart) return

    // ECharts otherwise includes the current axis-pointer selection in the PNG.
    chart.dispatchAction({ type: 'hideTip' })
    window.requestAnimationFrame(() => {
      const chartImage = chart.getDataURL({
        type: 'png',
        pixelRatio: 2,
        backgroundColor: exportBackground,
        excludeComponents: ['toolbox'],
      })
      if (!exportTitle) {
        saveImage(chartImage)
        return
      }

      const image = new Image()
      image.onload = () => {
        const pixelRatio = image.naturalWidth / chart.getWidth()
        const titleHeight = Math.round(42 * pixelRatio)
        const canvas = document.createElement('canvas')
        canvas.width = image.naturalWidth
        canvas.height = image.naturalHeight + titleHeight
        const context = canvas.getContext('2d')
        if (!context) {
          saveImage(chartImage)
          return
        }
        context.fillStyle = exportBackground
        context.fillRect(0, 0, canvas.width, canvas.height)
        context.fillStyle = isDark ? '#e8f5ff' : '#16324a'
        context.font = `600 ${Math.round(16 * pixelRatio)}px sans-serif`
        context.textBaseline = 'middle'
        context.fillText(exportTitle, Math.round(12 * pixelRatio), Math.round(22 * pixelRatio))
        context.drawImage(image, 0, titleHeight)
        saveImage(canvas.toDataURL('image/png'))
      }
      image.src = chartImage
    })
  }

  return (
    <div className="clinical-chart-export-wrap">
      <button
        type="button"
        className="clinical-chart-export-button"
        onClick={downloadChart}
        aria-label="Download chart as PNG"
        title="Download chart as PNG"
      >
        <Download size={15} />
      </button>
      <ReactECharts
        key={isDark ? 'dark' : 'light'}
        ref={chartRef}
        className={className}
        option={exportOption}
        onEvents={onEvents}
        theme={isDark ? 'dark' : undefined}
        style={{ height, width: '100%' }}
        notMerge
        lazyUpdate
      />
    </div>
  )
}

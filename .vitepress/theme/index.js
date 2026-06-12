import DefaultTheme from 'vitepress/theme'
import './custom.css'
import DecisionDashboard from './DecisionDashboard.vue'
import PositionCard from './components/PositionCard.vue'
import PositionDashboard from './components/PositionDashboard.vue'
import RiskDashboard from './components/RiskDashboard.vue'

export default {
  extends: DefaultTheme,
  enhanceApp({ app }) {
    app.component('DecisionDashboard', DecisionDashboard)
    app.component('PositionCard', PositionCard)
    app.component('PositionDashboard', PositionDashboard)
    app.component('RiskDashboard', RiskDashboard)
  }
}

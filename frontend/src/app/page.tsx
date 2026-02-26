import Link from 'next/link';
import styles from './page.module.css';
import { Target, Eye, ShieldAlert, Zap, ArrowRight, ShieldCheck, BarChart3, Globe, Shield, Activity, Lock } from 'lucide-react';

export default function Home() {
  return (
    <div className={styles.container}>
      {/* Immersive Background Effects */}
      <div className={styles.bgGlow1}></div>
      <div className={styles.bgGlow2}></div>

      {/* Hero Section */}
      <section className={styles.heroSection}>
        <div className={styles.heroGrid}>
          <div className={styles.heroContent}>
            <div className={styles.badge}>
              <span className={styles.pulseDot}></span>
              Rakshak Core v2.0 Live
            </div>
            <h1 className={styles.heroTitle}>
              Securing supply chains with <br />
              <span className={styles.highlightText}>Predictive AI.</span>
            </h1>
            <p className={styles.heroSubtitle}>
              Transform your logistics network into an impenetrable fortress. Rakshak AI fuses real-time computer vision, geospatial intelligence, and behavioral analytics to predict and prevent cargo theft before it occurs.
            </p>
            <div className={styles.ctaGroup}>
              <Link href="/dashboard" className={styles.primaryBtn}>
                Launch Command Center <ArrowRight size={18} />
              </Link>
              <Link href="/live-monitoring" className={styles.secondaryBtn}>
                Watch Vision Demo
              </Link>
            </div>

            {/* Trust Metrics */}
            <div className={styles.statsRow}>
              <div className={styles.statItem}>
                <h4>99.2%</h4>
                <p>Threat Detection Rate</p>
              </div>
              <div className={styles.statDivider}></div>
              <div className={styles.statItem}>
                <h4>&lt;50ms</h4>
                <p>Vision Model Latency</p>
              </div>
              <div className={styles.statDivider}></div>
              <div className={styles.statItem}>
                <h4>₹2.5B+</h4>
                <p>Cargo Value Secured</p>
              </div>
            </div>
          </div>

          {/* Hero Visual */}
          <div className={styles.heroVisual}>
            <div className={styles.visualContainer}>
              <img
                src="https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?q=80&w=2070&auto=format&fit=crop"
                alt="Logistics Operations"
                className={styles.mainImage}
              />
              <div className={styles.imageOverlay}></div>

              {/* Dynamic Floating Elements */}
              <div className={styles.floatingCard} style={{ top: '15%', left: '-12%', animationDelay: '0s' }}>
                <ShieldCheck className={styles.floatIconSafe} />
                <div className={styles.floatText}>
                  <strong>TR-8902 Secured</strong>
                  <span>Route deviation: None</span>
                </div>
              </div>

              <div className={styles.floatingCard} style={{ bottom: '25%', right: '-8%', animationDelay: '2s' }}>
                <Activity className={styles.floatIconAccent} />
                <div className={styles.floatText}>
                  <strong>Live Risk Engine</strong>
                  <span>Analyzing 124 parameters</span>
                </div>
              </div>

              <div className={styles.floatingIndicator}>
                <div className={styles.radarPing}></div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Ticker Section */}
      <div className={styles.tickerSection}>
        <p className={styles.tickerLabel}>POWERED BY STATE-OF-THE-ART TECHNOLOGY</p>
        <div className={styles.tickerTrack}>
          <span>TensorFlow</span> • <span>PyTorch</span> • <span>YOLOv8 Object Detection</span> •
          <span>DeepSORT Tracking</span> • <span>Isolation Forests</span> • <span>Django REST</span> •
          <span>Next.js</span> • <span>Leaflet Geospatial</span> • <span>Supabase</span>
        </div>
      </div>

      {/* Features - Bento Grid */}
      <section className={styles.bentoSection}>
        <div className={styles.sectionHeader}>
          <h2>Enterprise-Grade Capabilities</h2>
          <p>A unified security ecosystem built for scale, speed, and precision.</p>
        </div>

        <div className={styles.bentoGrid}>
          {/* Large Card */}
          <div className={`${styles.bentoCard} ${styles.bentoLarge}`}>
            <div className={styles.bentoBgGraphic1}></div>
            <div className={styles.bentoContent}>
              <div className={styles.iconWrapper}><Target className={styles.icon} /></div>
              <h3>Predictive Risk Modeling</h3>
              <p>Our machine learning models ingest years of historical crime data, cross-referenced with live weather, traffic conditions, and socio-economic markers to map high-risk zones dynamically.</p>
              <ul className={styles.featureList}>
                <li><Shield size={16} /> Route Vulnerability Scoring</li>
                <li><Shield size={16} /> Real-time Weather Integration</li>
                <li><Shield size={16} /> Historical Crime Indexing</li>
              </ul>
            </div>
          </div>

          <div className={styles.bentoCard}>
            <div className={styles.bentoContent}>
              <div className={styles.iconWrapper}><Eye className={styles.icon} /></div>
              <h3>Computer Vision Edge</h3>
              <p>Turn standard cameras into intelligent sensors. Instantly detect loitering, unauthorized access, and weapon presence.</p>
            </div>
          </div>

          <div className={styles.bentoCard}>
            <div className={styles.bentoContent}>
              <div className={styles.iconWrapper}><Globe className={styles.icon} /></div>
              <h3>Global Fleet Tracking</h3>
              <p>Monitor thousands of consignments simultaneously on a unified global dashboard with millisecond latency.</p>
            </div>
          </div>

          <div className={`${styles.bentoCard} ${styles.bentoWide}`}>
            <div className={styles.bentoBgGraphic2}></div>
            <div className={styles.bentoContent}>
              <div className={styles.iconWrapper}><Zap className={styles.icon} /></div>
              <h3>Autonomous Threat Response</h3>
              <p>When the Fusion engine detects a multi-vector threat, the system automatically triggers lock-down procedures, reroutes the vehicle, and alerts local authorities without requiring human intervention.</p>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works Timeline */}
      <section className={styles.workflowSection}>
        <div className={styles.sectionHeader}>
          <h2>The Rakshak Architecture</h2>
          <p>How our multi-agent AI system defends your freight.</p>
        </div>

        <div className={styles.timeline}>
          <div className={styles.timelineStep}>
            <div className={styles.stepNumber}>01</div>
            <h3>Perception</h3>
            <p>IoT sensors and cameras feed raw telemetry to our Edge AI.</p>
          </div>
          <div className={styles.timelineConnector}></div>
          <div className={styles.timelineStep}>
            <div className={styles.stepNumber}>02</div>
            <h3>Behavioral Analysis</h3>
            <p>Isolation Forests detect anomalies in speed, routing, and stops.</p>
          </div>
          <div className={styles.timelineConnector}></div>
          <div className={styles.timelineStep}>
            <div className={styles.stepNumber}>03</div>
            <h3>Risk Fusion</h3>
            <p>All streams merge into a single, highly accurate risk score.</p>
          </div>
          <div className={styles.timelineConnector}></div>
          <div className={styles.timelineStep}>
            <div className={styles.stepNumber}>04</div>
            <h3>Action</h3>
            <p>System triggers automated lockdown and sends rapid SMS alerts.</p>
          </div>
        </div>
      </section>

      {/* CTA Footer Section */}
      <section className={styles.ctaFooter}>
        <div className={styles.ctaFooterInner}>
          <Lock className={styles.ctaIcon} size={48} />
          <h2>Ready to secure your logistics?</h2>
          <p>Join top-tier enterprises deploying Rakshak AI to virtually eliminate cargo theft.</p>
          <Link href="/dashboard" className={styles.primaryBtnLarge}>
            Access the Platform
          </Link>
        </div>
      </section>
    </div>
  );
}

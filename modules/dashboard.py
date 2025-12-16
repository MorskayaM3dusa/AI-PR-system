# modules/dashboard.py
"""
Полный дашборд с реальными данными из базы
С поддержкой ежедневных обновлений
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta, date
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from database import SessionLocal, ProductMention, LLMResponse, GeneratedContent, AnalysisSession
import config

class Dashboard:
    def __init__(self):
        self.setup_page()
    
    def setup_page(self):
        """Настройка страницы"""
        st.set_page_config(
            page_title="AI Influence Dashboard",
            page_icon="🤖",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        st.markdown("""
        <style>
        .main {
            background-color: #0E1117;
            color: white;
        }
        .stMetric {
            background-color: #262730;
            padding: 10px;
            border-radius: 10px;
            border: 1px solid #444;
        }
        .stDataFrame {
            background-color: #262730;
        }
        h1, h2, h3, h4 {
            color: white !important;
        }
        </style>
        """, unsafe_allow_html=True)
    
    def get_mentions_over_time(self, days_back=30):
        """Получает данные об упоминаниях за период"""
        db = SessionLocal()
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days_back)
            
            mentions = db.query(
                ProductMention,
                LLMResponse.created_at
            ).join(LLMResponse).filter(
                LLMResponse.created_at >= start_date,
                LLMResponse.created_at <= end_date
            ).all()
            
            timeline_data = {}
            
            for mention, created_at in mentions:
                date = created_at.date()
                product = mention.product_name
                
                if date not in timeline_data:
                    timeline_data[date] = {}
                
                if product not in timeline_data[date]:
                    timeline_data[date][product] = 0
                
                timeline_data[date][product] += 1

            result = []
            for date, products in timeline_data.items():
                for product, count in products.items():
                    result.append({
                        'date': date,
                        'product': product,
                        'count': count
                    })
            
            return pd.DataFrame(result) if result else pd.DataFrame()
            
        finally:
            db.close()
    
    def get_product_stats(self):
        """Получает статистику по продуктам"""
        db = SessionLocal()
        try:
            all_products = [config.TARGET_PRODUCT] + config.COMPETITORS
            product_stats = {}
            
            for product in all_products:
                mentions = db.query(ProductMention).filter(
                    ProductMention.product_name.ilike(f"%{product}%")
                ).all()
                
                if mentions:
                    total = len(mentions)
                    sentiment_counts = {'positive': 0, 'neutral': 0, 'negative': 0}
                    
                    for mention in mentions:
                        if mention.sentiment in sentiment_counts:
                            sentiment_counts[mention.sentiment] += 1
                    positive_pct = (sentiment_counts['positive'] / total * 100) if total > 0 else 0
                    all_attributes = []
                    for mention in mentions:
                        if mention.attributes:
                            import json
                            try:
                                attrs = json.loads(mention.attributes)
                                all_attributes.extend(attrs)
                            except:
                                pass
                    from collections import Counter
                    top_attributes = Counter(all_attributes).most_common(3)
                    
                    product_stats[product] = {
                        'total': total,
                        'sentiment': sentiment_counts,
                        'positive_percentage': positive_pct,
                        'top_attributes': top_attributes,
                        'mentions_per_day': round(total / 7, 1) if total > 0 else 0
                    }
            return product_stats
        finally:
            db.close()
    def get_roi_data(self):
        """Рассчитывает данные ROI"""
        db = SessionLocal()
        try:
            content_items = db.query(GeneratedContent).count()
            total_mentions = db.query(ProductMention).count()
            target_mentions = db.query(ProductMention).filter(
                ProductMention.product_name.ilike(f"%{config.TARGET_PRODUCT}%")
            ).count()
            positive_target_mentions = db.query(ProductMention).filter(
                ProductMention.product_name.ilike(f"%{config.TARGET_PRODUCT}%"),
                ProductMention.sentiment == 'positive'
            ).count()
            positive_pct = (positive_target_mentions / target_mentions * 100) if target_mentions > 0 else 0
            content_cost = content_items * 50
            estimated_value = positive_target_mentions * 100
            roi_percentage = ((estimated_value - content_cost) / content_cost * 100) if content_cost > 0 else 0
            
            return {
                'content_items': content_items,
                'total_mentions': total_mentions,
                'target_mentions': target_mentions,
                'positive_target_mentions': positive_target_mentions,
                'positive_percentage': positive_pct,
                'content_cost': content_cost,
                'estimated_value': estimated_value,
                'roi_percentage': roi_percentage
            }
            
        finally:
            db.close()
    
    def create_timeline_chart(self, timeline_df):
        """График временного ряда"""
        if timeline_df.empty:
            st.info("Нет данных для временного графика")
            return
        print(f"Тип данных в колонке 'date': {type(timeline_df['date'].iloc[0])}")
        try:
            if isinstance(timeline_df['date'].iloc[0], str):
                timeline_df['datetime'] = pd.to_datetime(timeline_df['date'])
            elif isinstance(timeline_df['date'].iloc[0], (pd.Timestamp, datetime)):
                timeline_df['datetime'] = pd.to_datetime(timeline_df['date'])
            elif isinstance(timeline_df['date'].iloc[0], date):
                timeline_df['datetime'] = pd.to_datetime(timeline_df['date'])
            else:
                st.error(f"Неизвестный тип даты: {type(timeline_df['date'].iloc[0])}")
                return
        except Exception as e:
            st.error(f"Ошибка преобразования дат: {e}")
            st.write("Первые 5 значений колонки 'date':")
            st.write(timeline_df['date'].head())
            return

        fig = go.Figure()

        colors = ['#4ECDC4', '#FF6B6B', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD']

        products = timeline_df['product'].unique()[:6]
        
        for i, product in enumerate(products):
            product_data = timeline_df[timeline_df['product'] == product]
            
            fig.add_trace(go.Scatter(
                x=product_data['datetime'],
                y=product_data['count'],
                mode='lines+markers',
                name=product,
                line=dict(width=2, color=colors[i]),
                marker=dict(size=6),
                hovertemplate=(
                    f"<b>{product}</b><br>"
                    "Дата: %{x|%d.%m.%Y %H:%M}<br>"
                    "Упоминания: %{y}<br>"
                    "<extra></extra>"
                )
            ))

        if len(timeline_df) > 0:
            min_date = timeline_df['datetime'].min()
            max_date = timeline_df['datetime'].max()

            date_range = (max_date - min_date).total_seconds() / 3600
            
            if date_range <= 24:
                dtick = 3 * 3600000
                tickformat = '%H:%M'
            elif date_range <= 72:
                dtick = 12 * 3600000
                tickformat = '%d.%m %H:%M'
            else:
                dtick = 24 * 3600000
                tickformat = '%d.%m'
            
            fig.update_layout(
                title='Динамика упоминаний по времени',
                height=500,
                xaxis_title="Дата",
                yaxis_title="Количество упоминаний",
                xaxis=dict(
                    tickformat=tickformat,
                    dtick=dtick,
                    tickangle=45,
                    showgrid=True,
                    gridcolor='rgba(255,255,255,0.1)',
                    gridwidth=1,
                    showline=True,
                    linecolor='rgba(255,255,255,0.3)',
                    tickfont=dict(size=10),
                    hoverformat='%d.%m.%Y %H:%M'
                ),
                yaxis=dict(
                    showgrid=True,
                    gridcolor='rgba(255,255,255,0.1)',
                    gridwidth=1,
                    showline=True,
                    linecolor='rgba(255,255,255,0.3)'
                ),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                hovermode='x unified',
                legend=dict(
                    yanchor="top",
                    y=0.99,
                    xanchor="left",
                    x=0.01,
                    bgcolor='rgba(0,0,0,0.5)',
                    bordercolor='rgba(255,255,255,0.3)',
                    borderwidth=1
                )
            )
        
        st.plotly_chart(fig, use_container_width=True)
        with st.expander("Информация о данных графика"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Период данных", f"{(max_date - min_date).days + 1} дней")
            
            with col2:
                st.metric("Всего точек данных", len(timeline_df))
            
            with col3:
                st.metric("Уникальных продуктов", len(products))
            st.write("Последние 10 записей:")
            recent_data = timeline_df.sort_values('datetime', ascending=False).head(10)[
                ['datetime', 'product', 'count']
            ].copy()
            recent_data['datetime'] = recent_data['datetime'].dt.strftime('%d.%m.%Y %H:%M')
            st.dataframe(recent_data, hide_index=True)
    
    def create_product_comparison(self, product_stats):
        """Создает сравнение продуктов"""
        if not product_stats:
            st.info("Нет данных для сравнения")
            return
        
        st.subheader("Сравнение с конкурентами")
        data = []
        for product, stats in product_stats.items():
            data.append({
                'Продукт': product,
                'Упоминания': stats['total'],
                'Позитивные, %': round(stats['positive_percentage'], 1),
                'Позитивных': stats['sentiment']['positive'],
                'Нейтральных': stats['sentiment']['neutral'],
                'Негативных': stats['sentiment']['negative'],
                'За день': stats['mentions_per_day']
            })
        
        df = pd.DataFrame(data)
        top_n = min(10, len(df))
        df_top = df.sort_values('Упоминания', ascending=False).head(top_n)
        col1, col2 = st.columns(2)
        
        with col1:
            fig1 = go.Figure()
            
            fig1.add_trace(go.Bar(
                x=df_top['Продукт'],
                y=df_top['Упоминания'],
                name='Упоминания',
                marker_color='#4ECDC4',
                text=df_top['Упоминания'],
                textposition='auto'
            ))
            
            fig1.update_layout(
                title='Топ продуктов по упоминаниям',
                height=400,
                xaxis_title="Продукт",
                yaxis_title="Количество упоминаний",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                xaxis=dict(tickangle=45)
            )
            
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            fig2 = go.Figure()
            
            fig2.add_trace(go.Pie(
                labels=df_top['Продукт'],
                values=df_top['Упоминания'],
                hole=0.4,
                textinfo='label+percent',
                marker=dict(colors=px.colors.qualitative.Pastel)
            ))
            
            fig2.update_layout(
                title='Распределение упоминаний',
                height=400,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                showlegend=True,
                legend=dict(
                    yanchor="top",
                    y=0.99,
                    xanchor="left",
                    x=1.05
                )
            )
            
            st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Детальная статистика")
        def highlight_target(row):
            if config.TARGET_PRODUCT.lower() in row['Продукт'].lower():
                return ['background-color: #2E7D32; color: white'] * len(row)
            return [''] * len(row)
        
        st.dataframe(
            df.style.apply(highlight_target, axis=1),
            use_container_width=True,
            hide_index=True
        )
    
    def create_roi_section(self, roi_data):
        """Создает секцию ROI"""
        st.subheader("ROI контент-кампании")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Стоимость контента",
                f"${roi_data['content_cost']:,}",
                help="Предполагаемая стоимость создания контента",
                delta_color="off"
            )
        
        with col2:
            st.metric(
                "Оценка влияния",
                f"${roi_data['estimated_value']:,}",
                help="Предполагаемая ценность упоминаний",
                delta_color="off"
            )
        
        with col3:
            roi_color = "normal" if roi_data['roi_percentage'] >= 0 else "inverse"
            st.metric(
                "ROI",
                f"{roi_data['roi_percentage']:.1f}%",
                delta_color=roi_color
            )
        
        with col4:
            st.metric(
                "Материалы",
                f"{roi_data['content_items']} шт",
                help="Количество сгенерированных материалов",
                delta_color="off"
            )
        
        col5, col6, col7, col8 = st.columns(4)
        
        with col5:
            st.metric(
                "Всего упоминаний",
                f"{roi_data['total_mentions']:,}",
                delta_color="off"
            )
        
        with col6:
            target_color = "normal" if roi_data['target_mentions'] > 0 else "inverse"
            st.metric(
                f"Упоминания {config.TARGET_PRODUCT}",
                f"{roi_data['target_mentions']:,}",
                delta_color=target_color
            )
        
        with col7:
            positive_color = "normal" if roi_data['positive_percentage'] > 50 else "inverse"
            st.metric(
                "Позитивных упоминаний",
                f"{roi_data['positive_target_mentions']:,}",
                delta_color=positive_color
            )
        
        with col8:
            st.metric(
                "Эффективность",
                f"{(roi_data['positive_percentage'] / 100):.2f}",
                help="Доля позитивных упоминаний",
                delta_color="off"
            )
        
        st.subheader("Визуализация ROI")
        roi_fig_data = pd.DataFrame({
            'Категория': ['Стоимость', 'Оценка влияния', 'Чистая прибыль'],
            'Сумма ($)': [
                roi_data['content_cost'],
                roi_data['estimated_value'],
                roi_data['estimated_value'] - roi_data['content_cost']
            ],
            'Цвет': ['#FF6B6B', '#4ECDC4', '#96CEB4']
        })
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=roi_fig_data['Категория'],
            y=roi_fig_data['Сумма ($)'],
            marker_color=roi_fig_data['Цвет'],
            text=[f"${x:,.0f}" for x in roi_fig_data['Сумма ($)']],
            textposition='auto',
        ))
        
        fig.update_layout(
            height=400,
            title='Финансовые показатели кампании',
            yaxis_title="Сумма ($)",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white')
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
    
    def create_dashboard(self):
        """Основная функция создания дашборда"""
        
        st.title("🤖 Дашборд влияния на ИИ")
        st.markdown(f"**🎯 Целевой продукт:** {config.TARGET_PRODUCT}")
        
        with st.spinner("Загрузка данных..."):
            timeline_df = self.get_mentions_over_time(30)
            product_stats = self.get_product_stats()
            roi_data = self.get_roi_data()
        
        st.subheader("Быстрые метрики")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_mentions = roi_data['total_mentions']
            st.metric("Всего записей", f"{total_mentions:,}")
        
        with col2:
            unique_products = len(product_stats)
            st.metric("Уникальных продуктов", f"{unique_products}")
        
        with col3:
            days_of_data = len(timeline_df['date'].unique()) if not timeline_df.empty else 0
            st.metric("Дней данных", f"{days_of_data}")
        
        with col4:
            content_items = roi_data['content_items']
            st.metric("Материалов создано", f"{content_items}")

        st.markdown("---")
        self.create_timeline_chart(timeline_df)

        st.markdown("---")
        self.create_product_comparison(product_stats)

        st.markdown("---")
        self.create_roi_section(roi_data)

def main():
    """Основная функция запуска дашборда"""
    try:
        dashboard = Dashboard()
        dashboard.create_dashboard()
    except Exception as e:
        st.error(f"Ошибка при запуске дашборда: {e}")

if __name__ == "__main__":
    main()
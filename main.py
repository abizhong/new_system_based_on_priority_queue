import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import numpy as np
from matplotlib import font_manager
import matplotlib.gridspec as gridspec
import datetime
import glob
import re

# ================= 1. 字体配置 =================
def set_ch_font():
    fonts = ['Arial Unicode MS', 'Heiti TC', 'SimHei', 'Microsoft YaHei', 'Songti SC']
    for f in fonts:
        if f in [font.name for font in font_manager.fontManager.ttflist]:
            plt.rcParams['font.sans-serif'] = [f]
            break
    plt.rcParams['axes.unicode_minus'] = False

set_ch_font()

# ================= 2. 数据解析逻辑 =================
def robust_date_parser(series):
    series = series.astype(str).str.replace(r'\s+', ' ', regex=True).str.strip()
    parsed = pd.to_datetime(series, errors='coerce')
    if parsed.isna().any():
        nan_mask = parsed.isna() & (series != 'nan')
        formats = ['%Y-%m-%d %H:%M:%S', '%m/%d/%Y %H:%M:%S', '%Y/%m/%d %H:%M:%S', '%d/%m/%Y %H:%M:%S']
        for fmt in formats:
            if not nan_mask.any(): break
            parsed.loc[nan_mask] = pd.to_datetime(series.loc[nan_mask], format=fmt, errors='coerce')
            nan_mask = parsed.isna() & (series != 'nan')
    return parsed

def load_and_combine_data(folder_path, start_date, end_date):
    all_files = sorted(glob.glob(os.path.join(folder_path, "*.csv")))
    if len(all_files) < 2:
        print(f"❌ 警告：在文件夹中未找到至少2个CSV文件（当前找到 {len(all_files)} 个）。将退回常规合并。")
        li = []
        for filename in all_files:
            try: df_temp = pd.read_csv(filename, low_memory=False, encoding='utf-8-sig')
            except: df_temp = pd.read_csv(filename, low_memory=False, encoding='gb18030')
            df_temp.columns = [str(c).strip().replace('\ufeff', '').replace('\n', '') for c in df_temp.columns]
            li.append(df_temp)
        if not li: return pd.DataFrame()
        full_df = pd.concat(li, axis=0, ignore_index=True)
    else:
        # 按文件名排序，确保文件的先后顺序明确
        print(f">>> 正在读取文件 1: {os.path.basename(all_files[0])}")
        try: df1 = pd.read_csv(all_files[0], low_memory=False, encoding='utf-8-sig')
        except: df1 = pd.read_csv(all_files[0], low_memory=False, encoding='gb18030')
        df1.columns = [str(c).strip().replace('\ufeff', '').replace('\n', '') for c in df1.columns]
        
        print(f">>> 正在读取文件 2: {os.path.basename(all_files[1])}")
        try: df2 = pd.read_csv(all_files[1], low_memory=False, encoding='utf-8-sig')
        except: df2 = pd.read_csv(all_files[1], low_memory=False, encoding='gb18030')
        df2.columns = [str(c).strip().replace('\ufeff', '').replace('\n', '') for c in df2.columns]
        
        # 寻找基准定位时间列（目的大区首次签入时间）
        possible_cols1 = [c for c in df1.columns if '签入时间' in c and '首次' in c]
        target_col1 = possible_cols1[0] if possible_cols1 else '目的大区首次签入时间'
        possible_cols2 = [c for c in df2.columns if '签入时间' in c and '首次' in c]
        target_col2 = possible_cols2[0] if possible_cols2 else '目的大区首次签入时间'
        
        # 临时解析时间用于时间窗切分
        df1['__Temp_Time'] = robust_date_parser(df1[target_col1])
        df2['__Temp_Time'] = robust_date_parser(df2[target_col2])
        
        # 【核心修改】：设定硬性切分点（2026年5月16日 18:00:00）
        cutoff_time = pd.Timestamp('2026-05-16 18:00:00')
        
        print(f">>> 正在执行硬切分过滤...")
        # 文件1只要切分点之前的记录
        df1_filtered = df1[df1['__Temp_Time'] < cutoff_time].copy()
        # 文件2只要切分点之后的记录（包含5月17号及后续所有数据）
        df2_filtered = df2[df2['__Temp_Time'] >= cutoff_time].copy()
        
        print(f"  -> CSV 1 提取保留了 {len(df1_filtered)} 条记录 (16号18点前)")
        print(f"  -> CSV 2 提取保留了 {len(df2_filtered)} 条记录 (16号18点后)")
        
        # 合并过滤后的数据集
        full_df = pd.concat([df1_filtered, df2_filtered], axis=0, ignore_index=True)
        full_df.drop(columns=['__Temp_Time'], errors='ignore', inplace=True)

    # 全局单号清洗与去重
    if '运单号' in full_df.columns:
        full_df['运单号'] = full_df['运单号'].astype(str).str.strip()
    full_df.drop_duplicates(subset=['运单号'], inplace=True)
    
    for col in ['注入口岸', '目的枢纽中心', '目的中心']:
        if col in full_df.columns:
            full_df[col] = full_df[col].astype(str).str.strip().str.upper()
            
    full_df = full_df[full_df['注入口岸'] == 'EWR'].copy()
    
    possible_cols = [c for c in full_df.columns if '签入时间' in c and '首次' in c]
    target_col = possible_cols[0] if possible_cols else '目的大区首次签入时间'
    
    full_df[target_col] = robust_date_parser(full_df[target_col])
    full_df = full_df[full_df[target_col].notnull()].copy()
    
    # 调整并过滤报表时间视窗
    full_df['Adj_Date'] = (full_df[target_col] + pd.Timedelta(hours=6)).dt.date
    s_dt = pd.to_datetime(start_date).date()
    e_dt = pd.to_datetime(end_date).date()
    full_df = full_df[(full_df['Adj_Date'] >= s_dt) & (full_df['Adj_Date'] <= e_dt)].copy()
    
    # 解析并提取后续的核心时效段
    t_cols = ['目的大区首次签入时间', '目的枢纽集包时间', '目的枢纽签出时间', '站点首次签入时间', '快递员领件时间', '妥投时间']
    for c in t_cols:
        if c in full_df.columns: 
            full_df[c] = robust_date_parser(full_df[c])
            
    # 计算 T1 至 T5 的段耗时
    full_df['T1'] = (full_df['目的枢纽集包时间'] - full_df[target_col]).dt.total_seconds()/3600
    full_df['T2'] = (full_df['目的枢纽签出时间'] - full_df['目的枢纽集包时间']).dt.total_seconds()/3600
    full_df['T3'] = (full_df['站点首次签入时间'] - full_df['目的枢纽签出时间']).dt.total_seconds()/3600
    full_df['T4'] = (full_df['快递员领件时间'] - full_df['站点首次签入时间']).dt.total_seconds()/3600
    full_df['T5'] = (full_df['妥投时间'] - full_df['快递员领件时间']).dt.total_seconds()/3600
    
    for t in ['T1','T2','T3','T4','T5']:
        full_df[t] = full_df[t].clip(lower=0, upper=72).fillna(0)
        
    def is_nd(row):
        if pd.isnull(row['妥投时间']): return False
        deadline = pd.Timestamp(row['Adj_Date']) + pd.Timedelta(days=1, hours=23, minutes=59, seconds=59)
        return row['妥投时间'] <= deadline
        
    full_df['is_next_day'] = full_df.apply(is_nd, axis=1)
    return full_df

# ================= 3. 核心绘图子逻辑 =================
def draw_trajectory_leadtime(ax, site_df, site_id, dates, dates_str, segments, legend_labels, theme_config):
    color_theme, _, _ = theme_config
    base_palette = sns.color_palette(color_theme, 12)
    colors_post = [
        base_palette[1], # T1
        base_palette[4], # T2
        base_palette[6], # T3
        base_palette[8], # T4
        base_palette[11] # T5
    ]
    data = site_df.groupby('Adj_Date')[segments].mean().reindex(dates).fillna(0)
    bottom = np.zeros(len(dates))
    for i, seg in enumerate(segments):
        vals = data[seg].values
        ax.bar(range(len(dates)), vals, bottom=bottom, color=colors_post[i], label=legend_labels[i], edgecolor='white', linewidth=0.8)
        text_color = 'black' if i < 2 else 'white'
        for k, v in enumerate(vals):
            if v > 0.5:
                ax.text(k, bottom[k] + v/2, f'{v:.1f}', ha='center', va='center', color=text_color, fontweight='bold', fontsize=8)
        bottom += vals
    for j, total in enumerate(bottom):
        ax.text(j, total + 0.3, f'{total:.1f}h', ha='center', fontweight='bold', fontsize=12, color='black')
    ax.set_xticks(range(len(dates)))
    ax.set_xticklabels(dates_str, fontsize=9)
    title_name = 'JFK系统' if site_id == 'JFK' else site_id
    ax.set_title(f'【{title_name}】轨迹耗时分布 (Hours)', fontsize=18)
    ax.legend(loc='upper left', bbox_to_anchor=(1.01, 1), fontsize=8, borderaxespad=0.)

def draw_nextday_rate_and_volume(ax, ax_twin, site_df, site_id, dates, dates_str, theme_config):
    _, bar_color, line_color = theme_config
    stats = site_df.groupby('Adj_Date').agg(total=('运单号','count'), nd_cnt=('is_next_day','sum')).reindex(dates).fillna(0)
    stats['rate'] = (stats['nd_cnt'] / stats['total'] * 100).fillna(0)
    sns.barplot(x=dates_str, y=stats['total'], color='lightgrey', alpha=0.4, label='当日总应达', ax=ax)
    sns.barplot(x=dates_str, y=stats['nd_cnt'], color=bar_color, label='次日达妥投', ax=ax)
    sns.lineplot(x=range(len(dates)), y=stats['rate'], marker='o', color=line_color, lw=3, ax=ax_twin)
    max_v = stats['total'].max() if stats['total'].max() > 0 else 1
    for i, row in stats.reset_index().iterrows():
        ax.text(i, row['total'] + (max_v*0.01), f'{int(row["total"])}', ha='center', fontweight='bold', fontsize=11, color='black')
        if row['nd_cnt'] > (max_v * 0.05):
            ax.text(i, row['nd_cnt']/2, f'{int(row["nd_cnt"])}', ha='center', va='center', color='white', fontweight='bold')
        ax_twin.text(i, row['rate'] + 2, f'{row["rate"]:.1f}%', color=line_color, ha='center', fontweight='bold')
    ax.set_title(f'【{site_id}】及时率与货量明细', fontsize=18)
    ax_twin.set_ylim(0, 110)

def draw_jfk_distribution(ax, jfk_df, dates_j, dates_str_j, sub_targets):
    dist = jfk_df.groupby(['Adj_Date', '目的中心'])['运单号'].count().unstack(fill_value=0).reindex(columns=sub_targets, fill_value=0).reindex(dates_j).fillna(0)
    b_dist = np.zeros(len(dates_j))
    j_colors = sns.color_palette("husl", 3)
    for i, center in enumerate(sub_targets):
        vals = dist[center].values
        ax.bar(range(len(dates_j)), vals, bottom=b_dist, label=center, color=j_colors[i], edgecolor='white')
        total_d = dist.sum(axis=1).values
        for j in range(len(dates_j)):
            if total_d[j] > 0 and vals[j] > (total_d[j] * 0.05):
                pct = (vals[j] / total_d[j] * 100)
                # 修复遗留的变量 v 未定义Bug，使用 vals[j] 保证精准定位
                ax.text(j, b_dist[j] + vals[j]/2, f'{int(vals[j])}\n({pct:.1f}%)', ha='center', va='center', color='white', fontweight='bold', fontsize=9)
        b_dist += vals
    for j, t in enumerate(dist.sum(axis=1).values):
        ax.text(j, t + 2, f'{int(t)}', ha='center', fontweight='bold', fontsize=12, color='black')
    ax.set_xticks(range(len(dates_j)))
    ax.set_xticklabels(dates_str_j)
    ax.set_title('图3：【JFK系统】站点货量分布', fontsize=22)
    ax.legend(loc='upper left', bbox_to_anchor=(1.01, 1))

# ================= 4. 主函数 =================
def generate_reports(df, start_date, end_date):
    print(">>> 正在基于硬切解耦数据生成全景看板...")
    sites_config = {
        'LDJ01': ("Blues", "#4C72B0", "#C44E52"),
        'TEB01': ("YlGn", "#55A868", "#FF9900"),
        'PNE01': ("Purples", "#7B52A8", "#E07B39"),
        'PHL01': ("OrRd", "#D94F3D", "#2E86AB"),
        'BDL01': ("GnBu", "#2E8B57", "#CD5C5C"),
        'BDR01': ("YlOrBr", "#D2691E", "#4682B4"),
        'JFK': ("RdPu", "#C44E8A", "#2E86AB"),
        'GED01': ("BuGn", "#17A2B8", "#D9A441")
    }
    segments = ['T1', 'T2', 'T3', 'T4', 'T5']
    legend_labels = ['EWR分拣', 'EWR调度', '干线运输', '站点分货', '妥投派送']

    # --- 全景看板大图 ---
    fig_panel = plt.figure(figsize=(30, 95))
    gs = gridspec.GridSpec(18, 2, figure=fig_panel, hspace=0.6, wspace=0.15)
    fig_panel.suptitle(f'GOFO NEXT DAY 运营全景看板 ({start_date} - {end_date})', fontsize=45, fontweight='bold', y=0.99)
    row_idx = 0
    all_sites = ['LDJ01', 'TEB01', 'PNE01', 'PHL01', 'BDL01', 'BDR01', 'GED01']
    
    for site in all_sites:
        s_df = df[(df['目的枢纽中心'] == 'EWR.H') & (df['目的中心'] == site)].copy()
        if s_df.empty:
            row_idx += 2
            continue
        dates = sorted(s_df['Adj_Date'].unique())
        dates_str = [d.strftime('%m-%d') for d in dates]
        
        ax_l = fig_panel.add_subplot(gs[row_idx, 0])
        draw_trajectory_leadtime(ax_l, s_df, site, dates, dates_str, segments, legend_labels, sites_config[site])
        
        ax_r = fig_panel.add_subplot(gs[row_idx, 1])
        ax_rt = ax_r.twinx()
        draw_nextday_rate_and_volume(ax_r, ax_rt, s_df, site, dates, dates_str, sites_config[site])
        row_idx += 2
        
        # 保存独立站点小图报表
        fig_s, axes_s = plt.subplots(2, 1, figsize=(18, 16))
        draw_trajectory_leadtime(axes_s[0], s_df, site, dates, dates_str, segments, legend_labels, sites_config[site])
        ax_st = axes_s[1].twinx()
        draw_nextday_rate_and_volume(axes_s[1], ax_st, s_df, site, dates, dates_str, sites_config[site])
        fig_s.tight_layout(rect=[0, 0, 0.9, 0.95])
        fig_s.savefig(f'Gofo_Site_Report_{site}.png', dpi=200)
        plt.close(fig_s)

    # JFK 系统大盘逻辑
    j_df = df[df['目的枢纽中心'] == 'JFK.H'].copy()
    if not j_df.empty:
        dj = sorted(j_df['Adj_Date'].unique())
        dsj = [d.strftime('%m-%d') for d in dj]
        
        ax_jl = fig_panel.add_subplot(gs[12, 0])
        draw_trajectory_leadtime(ax_jl, j_df, 'JFK', dj, dsj, segments, legend_labels, sites_config['JFK'])
        
        ax_jr = fig_panel.add_subplot(gs[12, 1])
        ax_jrt = ax_jr.twinx()
        draw_nextday_rate_and_volume(ax_jr, ax_jrt, j_df, 'JFK', dj, dsj, sites_config['JFK'])
        
        ax_jd = fig_panel.add_subplot(gs[14:16, :])
        draw_jfk_distribution(ax_jd, j_df, dj, dsj, ['JFK01', 'LGA01', 'FRG01'])
        
        fig_j, axes_j = plt.subplots(3, 1, figsize=(18, 24))
        draw_trajectory_leadtime(axes_j[0], j_df, 'JFK', dj, dsj, segments, legend_labels, sites_config['JFK'])
        ax_jt = axes_j[1].twinx()
        draw_nextday_rate_and_volume(axes_j[1], ax_jt, j_df, 'JFK', dj, dsj, sites_config['JFK'])
        draw_jfk_distribution(axes_j[2], j_df, dj, dsj, ['JFK01', 'LGA01', 'FRG01'])
        fig_j.tight_layout(rect=[0, 0, 0.9, 0.95])
        fig_j.savefig('Gofo_Site_Report_JFK_System.png', dpi=200)
        plt.close(fig_j)

    fig_panel.savefig('Gofo_Monitor_All_Sites_Panel.png', dpi=150, bbox_inches='tight')
    plt.close(fig_panel)

if __name__ == "__main__":
    CONFIG = {"DATA_FOLDER": "./data", "START_DATE": "2026-05-09", "END_DATE": "2026-05-20"}
    df_clean = load_and_combine_data(CONFIG["DATA_FOLDER"], CONFIG["START_DATE"], CONFIG["END_DATE"])
    if not df_clean.empty:
        generate_reports(df_clean, CONFIG["START_DATE"], CONFIG["END_DATE"])
        print("✨ 强力切换过滤成功！5/16 18:00之后的数据已强制锁定第二文件，去重与时及时率恢复正常。")
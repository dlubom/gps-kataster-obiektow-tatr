#!/usr/bin/env python3
"""PBI-112: deterministic point-only inspection of the two 2025 LAS clips.

Run from any directory. Dependencies: numpy, matplotlib, PyYAML (see analysis.json).
Example: PYTHONPATH=/tmp/lidar-2025-python .venv/bin/python \
 docs/asdlc/verification/PBI-112/2025-assessment/analysis.py
No reprojection, interpolation, triangulation, smoothing, catalog mutation or
source decimation. record_index is zero-based IN THE HASHED CLIP, not source LAZ.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import platform
import struct
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
DEFAULT_DATA = ROOT / 'build/research/lidar-2026-10-23'
SOURCE_COLORS = {79:'#8e44ad',80:'#167da7',81:'#d65f29',82:'#239664'}
MARK_COLORS = {'TPN':'#00bcd4','PIG':'#ff00e6'}
SETTINGS = {
    'excluded_classes':[7,18], 'exclude_withheld':True,
    'keep_overlap_class_12':True, 'point_index_origin':0,
    'context_halfwidth_m':15, 'section_half_length_m':12,
    'section_full_widths_m':[0.5,1.0,2.0],
    'radial_diagnostic_radii_m':[0.25,0.5,1,2,5,10],
    'vertical_spread_xy_cell_sizes_m':[0.25,0.5,1],
    'minimum_points_per_spread_cell':8,
    'cell_origin':'LAS clip minimum X/Y, fixed for each file',
    'view_elevations_deg':{'top':90,'exposure':8,'underside':-35},
    'catalogue_z_datum':'unknown; marker only, no vertical correction permitted',
    'cloud_z_datum':'PL-EVRF2007-NH from matched index; absent from LAS header',
    'projection':'orthographic; equal scale X,Y,Z; no surface; all accepted points drawn',
    'marker_proxy':'exact catalogue XY plus nearest accepted record Z; an UNMEASURED display anchor, not terrain/threshold',
    'actual_nearest_record':'preserved separately with its real XYZ and dx/dy; small black dot',
    'rgb':'LAS RGB uint16 divided by 65535; no color correction',
}
SITES = [
    {'slug':'pod-wanta','object':'MTW-0054','cave':'C-0711','inventory':'T.E-12.03',
     'name':'Jaskinia pod Wantą / Litworowy Dzwon','file':'pod-wanta-2025-both-positions.las',
     'exposure_azimuth_deg':202.5},
    {'slug':'sniezna','object':'MLZ-0068','cave':'C-0648','inventory':'T.E-13.01',
     'name':'Jaskinia Śnieżna','file':'sniezna-2025-100m.las','exposure_azimuth_deg':90.0},
]
FIELDS = ['clip','record_index','X_easting','Y_northing','Z','classification','PointSourceId',
          'return_number','number_of_returns','scan_direction_flag','edge_of_flight_line',
          'synthetic','keypoint','withheld','scan_angle_rank','gps_time','intensity','red','green','blue']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_las(path):
    raw=path.read_bytes(); h=raw[:227]
    assert h[:4]==b'LASF' and tuple(h[24:26])==(1,2)
    offset=struct.unpack_from('<I',h,96)[0]
    fmt=h[104]; size=struct.unpack_from('<H',h,105)[0]
    count=struct.unpack_from('<I',h,107)[0]
    assert fmt==3 and size==34 and len(raw)==offset+size*count
    scales=np.array(struct.unpack_from('<3d',h,131)); offsets=np.array(struct.unpack_from('<3d',h,155))
    dtype=np.dtype({'names':['x','y','z','intensity','bitfield','class_flags','scan_angle_rank','user_data','PointSourceId','gps_time','red','green','blue'],
        'formats':['<i4','<i4','<i4','<u2','u1','u1','i1','u1','<u2','<f8','<u2','<u2','<u2'],
        'offsets':[0,4,8,12,14,15,16,17,18,20,28,30,32], 'itemsize':size})
    r=np.frombuffer(raw,dtype=dtype,count=count,offset=offset)
    xyz=np.column_stack([r[a]*scales[i]+offsets[i] for i,a in enumerate(['x','y','z'])])
    a={k:r[k] for k in r.dtype.names}
    a.update({'xyz':xyz,'record_index':np.arange(count),'classification':r['class_flags']&31,
              'synthetic':(r['class_flags']>>5)&1,'keypoint':(r['class_flags']>>6)&1,
              'withheld':(r['class_flags']>>7)&1,'return_number':r['bitfield']&7,
              'number_of_returns':(r['bitfield']>>3)&7,'scan_direction_flag':(r['bitfield']>>6)&1,
              'edge_of_flight_line':(r['bitfield']>>7)&1})
    a['accepted']=~np.isin(a['classification'],SETTINGS['excluded_classes'])&(a['withheld']==0)
    a['rgb']=np.column_stack([r[k] for k in ['red','green','blue']])/65535.0
    a['header']={'count':count,'point_format':fmt,'point_record_bytes':size,'point_data_offset':offset,
                 'scales':scales.tolist(),'offsets':offsets.tolist()}
    a['clip']=path.name
    return a


def counts(x):
    v,n=np.unique(x,return_counts=True)
    return {str(int(k)):int(s) for k,s in zip(v,n)}


def point(a,i):
    d={'clip':a['clip'],'record_index':int(i)}
    for k,v in zip(['X_easting','Y_northing','Z'],a['xyz'][i]): d[k]=round(float(v),2)
    for k in FIELDS[5:]: d[k]=float(a[k][i]) if k=='gps_time' else int(a[k][i])
    return d


def write_csv(path,rows,fields=None):
    if not rows:return
    fields=fields or list(rows[0])
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fields,lineterminator="\n"); w.writeheader(); w.writerows(rows)


def local_uv(xyz,center,az):
    rad=np.deg2rad(az); outward=np.array([np.sin(rad),np.cos(rad)])
    right=np.array([np.cos(rad),-np.sin(rad)])
    delta=xyz[:,:2]-center
    return delta@outward,delta@right


def footer(fig,extra=''):
    fig.text(.02,.015,'Rzeczywiste odbicia; bez interpolacji. Wyłączono klasy 7/18 i withheld. '
             'Z chmury: EVRF2007-NH ze skorowidza. Z katalogu: datum unknown. '+extra,fontsize=8,color='#333333')


def scale_bar(ax,length=5):
    x0,x1=ax.get_xlim(); y0,y1=ax.get_ylim(); x=x0+.07*(x1-x0);y=y0+.07*(y1-y0)
    ax.plot([x,x+length],[y,y],color='black',lw=3)
    ax.text(x+length/2,y+.025*(y1-y0),f'{length:g} m',ha='center',fontsize=9,
            bbox={'facecolor':'white','edgecolor':'none','alpha':.7})


def mark2d(ax,measurements,center,with_z=False,az=None):
    for m in measurements:
        if az is None:x=m['X']-center[0];y=m['Y']-center[1]
        else:
            p,u=local_uv(np.array([[m['X'],m['Y'],0]]),center,az);x=u[0];y=m['Z']
        c=MARK_COLORS[m['source']]
        ax.scatter([x],[y],s=45,facecolors='none',edgecolors='black',linewidths=2,zorder=10)
        ax.scatter([x],[y],s=24,facecolors='none',edgecolors=c,linewidths=1.5,zorder=11)
        ax.annotate(f"{m['object']} {m['source']} {m['id']}",(x,y),xytext=(7,7),textcoords='offset points',fontsize=8,
                    bbox={'facecolor':'white','alpha':.8,'edgecolor':'none'},zorder=12)


def overview(site,a,ms,out):
    xyz=a['xyz'];mask=a['accepted'];center=(xyz[:,:2].min(0)+xyz[:,:2].max(0))/2
    fig,axs=plt.subplots(1,2,figsize=(14,10),layout='constrained')
    for ax,kind in zip(axs,['height','source']):
        order=np.flatnonzero(mask)
        if kind=='height':
            sc=ax.scatter(xyz[order,0]-center[0],xyz[order,1]-center[1],c=xyz[order,2],s=.1,cmap='terrain',rasterized=True)
            fig.colorbar(sc,ax=ax,shrink=.5,label='Z odbić [m], PL-EVRF2007-NH ze skorowidza')
        else:
            for sid in np.unique(a['PointSourceId']):
                ix=order[a['PointSourceId'][order]==sid]
                ax.scatter(xyz[ix,0]-center[0],xyz[ix,1]-center[1],s=.1,c=SOURCE_COLORS[int(sid)],rasterized=True)
            ax.legend(handles=[Line2D([],[],marker='o',ls='',color=c,label=f'PointSourceId {sid}') for sid,c in SOURCE_COLORS.items() if str(sid) in counts(a['PointSourceId'])],loc='upper right',fontsize=8)
        mark2d(ax,ms,center);ax.set_aspect('equal');ax.set_xlabel(f'Easting − {center[0]:.2f} [m]  → E')
        ax.set_ylabel(f'Northing − {center[1]:.2f} [m]  → N');ax.grid(alpha=.15);scale_bar(ax,10)
        ax.set_title('Wysokość rzeczywistych odbić' if kind=='height' else 'Grupy PointSourceId (niepotwierdzone kierunki nalotu)')
    fig.suptitle(f"{site['name']} — {site['object']} / {site['inventory']} — całość wycinka 2025")
    footer(fig);fig.savefig(out/f"{site['slug']}-overview.png",dpi=180);plt.close(fig)


def context_figure(site,a,ms,center,slug,out):
    xyz=a['xyz']; half=SETTINGS['context_halfwidth_m']
    mask=a['accepted']&(np.max(np.abs(xyz[:,:2]-center),axis=1)<=half);ii=np.flatnonzero(mask)
    local=xyz[ii].copy();local[:,:2]-=center
    zlim=(float(local[:,2].min()),float(local[:,2].max()))
    fig=plt.figure(figsize=(15,13));gs=fig.add_gridspec(2,2,left=.06,right=.96,bottom=.08,top=.91,wspace=.12,hspace=.25)
    ax=fig.add_subplot(gs[0,0]);sc=ax.scatter(local[:,0],local[:,1],c=local[:,2],cmap='terrain',s=2,linewidths=0)
    mark2d(ax,ms,center);ax.set_aspect('equal');ax.set_xlim(-half,half);ax.set_ylim(-half,half)
    ax.set_xlabel('ΔE [m] → E');ax.set_ylabel('ΔN [m] → N');ax.set_title('Z góry • wszystkie dopuszczone klasy • kolor Z');scale_bar(ax)
    fig.colorbar(sc,ax=ax,fraction=.035,pad=.01,label='Z [m]')
    az=site['exposure_azimuth_deg']; mplaz=90-az
    for pos,elev,title in [(gs[0,1],8,f"Od ekspozycji {az:g}° • elewacja kamery +8°"),(gs[1,0],-35,f"Od spodu, azymut {az:g}° • elewacja −35°")]:
        ax=fig.add_subplot(pos,projection='3d');ax.set_proj_type('ortho')
        ax.scatter(local[:,0],local[:,1],local[:,2],c=a['rgb'][ii],s=1,linewidths=0,depthshade=False)
        for m in ms:
            p=m['nearest_xy_record'];c=MARK_COLORS[m['source']]
            ax.scatter([m['X']-center[0]],[m['Y']-center[1]],[p['Z']],c=c,edgecolors='black',s=26,depthshade=False)
            ax.scatter([p['X_easting']-center[0]],[p['Y_northing']-center[1]],[p['Z']],c='black',s=5,depthshade=False)
            ax.text(m['X']-center[0],m['Y']-center[1],p['Z']+.8,f"{m['object']} {m['source']} XY@Z*",fontsize=7,
                    bbox={'facecolor':'white','alpha':.7,'edgecolor':'none'})
            if zlim[0]<=m['Z']<=zlim[1]:
                ax.scatter([m['X']-center[0]],[m['Y']-center[1]],[m['Z']],c=c,edgecolors='black',s=35,marker='X',depthshade=False)
                ax.text(m['X']-center[0],m['Y']-center[1],m['Z']-.8,f"{m['source']} XYZ (datum ?)",fontsize=7)
        ax.set_xlim(-half,half);ax.set_ylim(-half,half);ax.set_zlim(*zlim)
        ax.set_box_aspect([2*half,2*half,zlim[1]-zlim[0]])
        ax.view_init(elev=elev,azim=mplaz);ax.set_xlabel('ΔE [m]');ax.set_ylabel('ΔN [m]');ax.set_zlabel('Z [m]')
        ax.set_title(title,fontsize=11)
    ax=fig.add_subplot(gs[1,1]);ix=np.flatnonzero(mask&(a['classification']==2));l=xyz[ix].copy();l[:,:2]-=center
    sc=ax.scatter(l[:,0],l[:,1],c=l[:,2],cmap='terrain',s=3,linewidths=0,vmin=zlim[0],vmax=zlim[1])
    mark2d(ax,ms,center);ax.set_xlim(-half,half);ax.set_ylim(-half,half);ax.set_aspect('equal');ax.set_xlabel('ΔE [m] → E');ax.set_ylabel('ΔN [m] → N')
    ax.set_title('Z góry • tylko klasa 2 (nie gwarantuje progu)');scale_bar(ax)
    shown=', '.join(f"{m['source']} {m['id']}" for m in ms)
    fig.suptitle(f"{site['name']} — {shown}\nŚrodek E {center[0]:.2f}, N {center[1]:.2f}; okno 30×30 m; {len(ii):,} odbić; RGB natywne",fontsize=15)
    outside=[f"{m['source']} XYZ Z={m['Z']:.3f} poza skalą tej chmury" for m in ms if not zlim[0]<=m['Z']<=zlim[1]]
    footer(fig,'● XY@Z* umowny, niezmierzony; · rzeczywisty najbliższy rekord; X XYZ katalogu. '+ '; '.join(outside))
    fig.savefig(out/f'{slug}-views.png',dpi=185);plt.close(fig)


def source_figure(site,a,ms,center,slug,out):
    xyz=a['xyz'];half=12;mask=a['accepted']&(np.max(np.abs(xyz[:,:2]-center),axis=1)<=half)
    p,u=local_uv(xyz,center,site['exposure_azimuth_deg']);sids=np.unique(a['PointSourceId']);fig,axs=plt.subplots(2,len(sids),figsize=(4.2*len(sids),8),layout='constrained',squeeze=False)
    zmin,zmax=np.quantile(xyz[mask,2],[0,1])
    for col,sid in enumerate(sids):
        ix=mask&(a['PointSourceId']==sid);ax=axs[0,col]
        ax.scatter(xyz[ix,0]-center[0],xyz[ix,1]-center[1],s=1,c=xyz[ix,2],cmap='terrain',vmin=zmin,vmax=zmax)
        mark2d(ax,ms,center);ax.set_xlim(-half,half);ax.set_ylim(-half,half);ax.set_aspect('equal');ax.set_xlabel('ΔE [m]');ax.set_ylabel('ΔN [m]');scale_bar(ax)
        ax.set_title(f'PointSourceId {sid}: {ix.sum()} pkt')
        ix=ix&(np.abs(u)<=.5)&(np.abs(p)<=12);ax=axs[1,col]
        ax.scatter(p[ix],xyz[ix,2],s=6,c=SOURCE_COLORS[int(sid)]);ax.set_xlim(-12,12);ax.set_ylim(zmin-1,zmax+1)
        ax.set_aspect('equal',adjustable='box');ax.set_xlabel(f'Oś ekspozycji {site["exposure_azimuth_deg"]:g}° [m]');ax.set_ylabel('Z [m]');ax.grid(alpha=.2)
        ax.set_title(f'Przekrój 1 m: {ix.sum()} pkt')
    fig.suptitle(f"{slug}: grupy źródłowe osobno; wspólny zasięg i skala Z")
    footer(fig,'Grupy nie dowodzą różnych kierunków obserwacji.');fig.savefig(out/f'{slug}-sources.png',dpi=170);plt.close(fig)


def sections(site,a,m,out):
    center=np.array([m['X'],m['Y']]);xyz=a['xyz'];p,u=local_uv(xyz,center,site['exposure_azimuth_deg']);half=SETTINGS['section_half_length_m'];rows=[];summary=[]
    fig,axs=plt.subplots(2,3,figsize=(17,10));fig.subplots_adjust(left=.06,right=.98,bottom=.12,top=.88,wspace=.2,hspace=.28)
    local=a['accepted']&(np.hypot(*(xyz[:,:2]-center).T)<=half)
    zmin,zmax=xyz[local,2].min()-1,xyz[local,2].max()+1
    for row,(name,along,cross,az) in enumerate([('podłużny',p,u,site['exposure_azimuth_deg']),('poprzeczny',u,p,(site['exposure_azimuth_deg']+90)%360)]):
        for col,width in enumerate(SETTINGS['section_full_widths_m']):
            mask=a['accepted']&(abs(along)<=half)&(abs(cross)<=width/2);ix=np.flatnonzero(mask);ax=axs[row,col]
            for sid in np.unique(a['PointSourceId']):
                inds=ix[a['PointSourceId'][ix]==sid]
                ax.scatter(along[inds],xyz[inds,2],s=7,c=SOURCE_COLORS[int(sid)],alpha=.8,linewidths=0)
            ground=ix[a['classification'][ix]==2]
            ax.scatter(along[ground],xyz[ground,2],s=12,facecolors='none',edgecolors='black',linewidths=.25)
            ax.axvline(0,c='#555555',lw=.7,ls='--');ax.set_xlim(-half,half);ax.set_ylim(zmin,zmax);ax.set_aspect('equal',adjustable='box');ax.grid(alpha=.2)
            pr=m['nearest_xy_record'];prxyz=np.array([[pr['X_easting'],pr['Y_northing'],pr['Z']]])
            pp,uu=local_uv(prxyz,center,site['exposure_azimuth_deg']);coord=pp[0] if row==0 else uu[0]
            ax.scatter([coord],[pr['Z']],s=8,c='black',zorder=9)
            ax.scatter([0],[pr['Z']],s=40,c=MARK_COLORS[m['source']],edgecolors='black',zorder=8)
            if zmin<=m['Z']<=zmax:ax.scatter([0],[m['Z']],s=42,c=MARK_COLORS[m['source']],edgecolors='black',marker='X',zorder=8)
            else:ax.text(.02,.97,f"XYZ katalogu Z={m['Z']:.3f}: poza skalą",transform=ax.transAxes,va='top',fontsize=7)
            ax.set_title(f'{name} {az:g}° | pełna szerokość {width:g} m\n{len(ix)} pkt, klasa 2: {len(ground)}',fontsize=10)
            ax.set_xlabel('Odległość od XY [m]; + w kierunku azymutu');ax.set_ylabel('Z [m]')
            summary.append({'orientation':name,'azimuth_deg':az,'full_width_m':width,'count':len(ix),'class_counts':counts(a['classification'][ix]),'PointSourceId_counts':counts(a['PointSourceId'][ix])})
            if width==1.0:
                for i in ix:
                    rows.append({'section':name,'along_m':round(float(along[i]),6),'cross_m':round(float(cross[i]),6),**point(a,i)})
    handles=[Line2D([],[],marker='o',ls='',color=c,label=f'PointSourceId {sid}') for sid,c in SOURCE_COLORS.items() if str(sid) in counts(a['PointSourceId'])]
    handles += [Line2D([],[],marker='o',ls='',color='black',markerfacecolor='none',label='obrys: klasa 2'),Line2D([],[],marker='X',ls='',color=MARK_COLORS[m['source']],label='XYZ katalog (datum ?)'),Line2D([],[],marker='o',ls='',color=MARK_COLORS[m['source']],label='XY@Z* umowny, niezmierzony')]
    fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,.035),ncol=4,fontsize=8)
    fig.suptitle(f"{site['name']} — {m['object']} {m['source']} {m['id']} — przekroje przez zapisane XY\nE {m['X']:.2f}, N {m['Y']:.2f}; brak interpolacji; 0,5 / 1 / 2 m to pełne szerokości",fontsize=15)
    footer(fig);slug=f"{site['slug']}-{m['source'].lower()}";fig.savefig(out/f'{slug}-sections.png',dpi=190);plt.close(fig)
    write_csv(out/f'{slug}-sections-1m.csv',rows)
    return summary


def marker_z_figure(sites,clouds,out):
    fig,axs=plt.subplots(1,4,figsize=(16,9));fig.subplots_adjust(bottom=.12,top=.85,left=.05,right=.99,wspace=.25)
    col=0
    for site in sites:
        a=clouds[site['slug']]
        for m in site['measurements']:
            ax=axs[col];col+=1;xyz=a['xyz'];d=xyz[:,:2]-[m['X'],m['Y']];mask=a['accepted']&(np.hypot(d[:,0],d[:,1])<=5)
            ax.scatter(d[mask,0],xyz[mask,2],s=2,c='#778899',alpha=.8)
            pr=m['nearest_xy_record'];c=MARK_COLORS[m['source']]
            ax.scatter([0],[m['Z']],c=c,edgecolors='black',marker='X',s=45,zorder=10)
            ax.annotate(f"XYZ katalogu\nZ {m['Z']:.6f}\ndatum unknown",(0,m['Z']),xytext=(.04,.94),textcoords='axes fraction',fontsize=8,va='top',bbox={'facecolor':'white','alpha':.9,'edgecolor':'none'},arrowprops={'arrowstyle':'-','color':'#444444','lw':.6})
            ax.scatter([pr['dx_m']],[pr['Z']],c='black',s=8,zorder=11)
            ax.scatter([0],[pr['Z']],c=c,edgecolors='black',s=35,zorder=10)
            ax.annotate(f"XY@Z* umowny, niezmierzony\nZ rekordu {pr['record_index']}: {pr['Z']:.2f}\ndXY do rekordu {pr['distance_xy_m']:.3f} m",(0,pr['Z']),xytext=(.04,.06),textcoords='axes fraction',fontsize=8,va='bottom',bbox={'facecolor':'white','alpha':.9,'edgecolor':'none'},arrowprops={'arrowstyle':'-','color':'#444444','lw':.6})
            ax.set_xlim(-6,6);mn=min(m['Z'],xyz[mask,2].min());mx=max(m['Z'],xyz[mask,2].max());ax.set_ylim(mn-3,mx+5)
            ax.set_title(f"{m['object']} {m['source']}\nE {m['X']:.2f}\nN {m['Y']:.2f}");ax.set_xlabel('ΔE [m]; promień XY 5 m');ax.set_ylabel('Wartość Z [m]');ax.grid(alpha=.2)
    fig.suptitle('XYZ katalogu (X), umowny XY@Z* (●), rzeczywiste najbliższe odbicie (·)\nWspólny wykres wartości liczbowych NIE uzgadnia datum i NIE wyznacza korekty wysokości',fontsize=15)
    footer(fig,'Z* pobrano z najbliższego odbicia; nie zmierzono takiego XYZ. Skale paneli różne.');fig.savefig(out/'markers-xyz-vs-xy.png',dpi=180);plt.close(fig)


# These windows were selected AFTER looking at the exact-point views/sections.
# They are observation windows, not measured entrance outlines or error bounds.
CANDIDATE_WINDOWS = {
 'pod-wanta':{'candidate_id':'PW-C1','position_source':'TPN',
   'roi_xy':[566318.8,566324.0,153074.0,153077.5],
   'lower_box_xyz':[566319.6,566323.4,153074.7,153076.9,1786.0,1790.1],
   'upper_z_min':1791.0,'plot_z':[1785.5,1796.0],
   'representative_pairs':[[239962,466382],[241882,395366]]},
 'sniezna':{'candidate_id':'SN-C1','position_source':'TPN',
   'roi_xy':[567412.5,567416.0,152930.8,152935.3],
   'lower_box_xyz':[567413.55,567414.7,152932.1,152934.1,1696.8,1698.05],
   'upper_z_min':1699.5,'plot_z':[1696.0,1705.0],
   'representative_pairs':[[88032,241271],[88034,24060]]},
}


def candidates(sites,clouds,out,support):
    results=[];pairs_out=[];cellrows=[]
    for site in sites:
        cfg=CANDIDATE_WINDOWS[site['slug']];a=clouds[site['slug']];xyz=a['xyz'];cid=cfg['candidate_id']
        x0,x1,y0,y1=cfg['roi_xy'];bx0,bx1,by0,by1,bz0,bz1=cfg['lower_box_xyz']
        roi=a['accepted']&(xyz[:,0]>=x0)&(xyz[:,0]<=x1)&(xyz[:,1]>=y0)&(xyz[:,1]<=y1)
        low=roi&(xyz[:,0]>=bx0)&(xyz[:,0]<=bx1)&(xyz[:,1]>=by0)&(xyz[:,1]<=by1)&(xyz[:,2]>=bz0)&(xyz[:,2]<=bz1)
        ii=np.flatnonzero(roi);li=np.flatnonzero(low)
        data={'candidate_id':cid,'status':'potential_structure; entrance and threshold unconfirmed',
            'selection':'manual observation window after exact-point views; NOT a detected opening outline',
            'parameters':cfg,'lower_selected_points':len(li),'lower_class_counts':counts(a['classification'][li]),
            'lower_PointSourceId_counts':counts(a['PointSourceId'][li]),
            'lower_actual_xyz_min':xyz[li].min(0).tolist(),'lower_actual_xyz_max':xyz[li].max(0).tolist(),
            'lower_sample_centroid_xyz':xyz[li].mean(0).tolist(),
            'centroid_meaning':'unweighted sample centroid; sensitive to chosen box, density and occlusion; NOT entrance position or correction',
            'lower_by_source':{},'stacked_cells':{},'representative_pairs':[],
            'lower_class2_sensitivity':{'n':int(np.sum(a['classification'][li]==2)), 'centroid_xyz':xyz[li[a['classification'][li]==2]].mean(0).tolist()},
            'lower_unique_source_gps_time_pairs':len(set((int(a['PointSourceId'][i]),float(a['gps_time'][i])) for i in li))}
        for sid in np.unique(a['PointSourceId']):
            jj=li[a['PointSourceId'][li]==sid]
            if len(jj):data['lower_by_source'][str(int(sid))]={'n':len(jj),'classes':counts(a['classification'][jj]),'min_xyz':xyz[jj].min(0).tolist(),'max_xyz':xyz[jj].max(0).tolist(),'centroid_xyz':xyz[jj].mean(0).tolist()}
        # Explicit 0.5 m cells, anchored at clipped file minima. Counts use all
        # returns, including duplicate XY / successive returns from one pulse.
        origin=xyz[:,:2].min(0);cells=np.floor((xyz[ii,:2]-origin)/.5).astype(int)
        keys,inv=np.unique(cells,axis=0,return_inverse=True)
        for subset in ['accepted','class2']:
            subset_results=[]
            for k,key in enumerate(keys):
                jj=ii[inv==k]
                if subset=='class2':jj=jj[a['classification'][jj]==2]
                lower=jj[low[jj]];upper=jj[xyz[jj,2]>=cfg['upper_z_min']]
                if len(lower)>=2 and len(upper)>=2:
                    cellmin=origin+key*.5
                    item={'candidate_id':cid,'subset':subset,'cell_Xmin':round(float(cellmin[0]),2),'cell_Ymin':round(float(cellmin[1]),2),
                          'cell_size_m':.5,'lower_count':len(lower),'upper_count':len(upper),
                          'lower_z_min':float(xyz[lower,2].min()),'lower_z_max':float(xyz[lower,2].max()),
                          'upper_z_min':float(xyz[upper,2].min()),'upper_z_max':float(xyz[upper,2].max()),
                          'lower_sources':';'.join(counts(a['PointSourceId'][lower])),
                          'upper_sources':';'.join(counts(a['PointSourceId'][upper])),
                          'lower_source_counts':json.dumps(counts(a['PointSourceId'][lower]),sort_keys=True),
                          'upper_source_counts':json.dumps(counts(a['PointSourceId'][upper]),sort_keys=True),
                          'lower_record_indices':';'.join(map(str,lower)), 'upper_record_indices':';'.join(map(str,upper))}
                    cellrows.append(item);subset_results.append(item)
            data['stacked_cells'][subset]=len(subset_results)
            data['stacked_cells'][subset+'_by_same_PointSourceId']={str(int(sid)):sum(json.loads(row['lower_source_counts']).get(str(int(sid)),0)>=2 and json.loads(row['upper_source_counts']).get(str(int(sid)),0)>=2 for row in subset_results) for sid in np.unique(a['PointSourceId'])}
        # All nearly covertical point pairs in this ROI with separation >=1.3m.
        # No surface/model, and no interpretation as opening size.
        for ia,i in enumerate(ii):
            jj=ii[ia+1:];dd=np.linalg.norm(xyz[jj,:2]-xyz[i,:2],axis=1);dz=abs(xyz[jj,2]-xyz[i,2]);matches=jj[(dd<=.12)&(dz>=1.3)]
            for j in matches:
                l,h=sorted([int(i),int(j)],key=lambda k:xyz[k,2])
                pairs_out.append({'candidate_id':cid,'lower_record_index':l,'upper_record_index':h,'distance_xy_m':float(np.linalg.norm(xyz[l,:2]-xyz[h,:2])),
                                  'delta_z_m':float(xyz[h,2]-xyz[l,2]),'lower_class':int(a['classification'][l]),'upper_class':int(a['classification'][h]),
                                  'lower_PointSourceId':int(a['PointSourceId'][l]),'upper_PointSourceId':int(a['PointSourceId'][h])})
        for k,(l,h) in enumerate(cfg['representative_pairs'],1):
            assert roi[l] and roi[h] and xyz[l,2]<xyz[h,2]
            d={'pair_id':f'{cid}-P{k}','lower':point(a,l),'upper':point(a,h),'distance_xy_m':float(np.linalg.norm(xyz[l,:2]-xyz[h,:2])),'delta_z_m':float(xyz[h,2]-xyz[l,2])}
            data['representative_pairs'].append(d)
            for typ,i in [('lower',l),('upper',h)]:support.append({'role':f'{cid} pair{k} {typ}; actual return, interpretation unconfirmed',**point(a,i)})
        rows=[{'candidate_id':cid,'selected_lower_box':int(low[i]),**point(a,i)} for i in ii]
        write_csv(out/f'{site["slug"]}-candidate-points.csv',rows)
        m=next(m for m in site['measurements'] if m['source']=='TPN');center=np.array([m['X'],m['Y']]);p,u=local_uv(xyz,center,site['exposure_azimuth_deg'])
        fig,axs=plt.subplots(2,2,figsize=(13,12));fig.subplots_adjust(top=.87,bottom=.16,hspace=.27,wspace=.22,left=.07,right=.98)
        ax=axs[0,0];sc=ax.scatter(xyz[ii,0]-center[0],xyz[ii,1]-center[1],c=xyz[ii,2],cmap='terrain',s=9,linewidths=0)
        ax.scatter(xyz[li,0]-center[0],xyz[li,1]-center[1],facecolors='none',edgecolors='black',s=18,linewidths=.4)
        from matplotlib.patches import Rectangle
        ax.add_patch(Rectangle((bx0-center[0],by0-center[1]),bx1-bx0,by1-by0,fill=False,edgecolor='#c62828',lw=1,ls='--'))
        mark2d(ax,[m],center);ax.set_aspect('equal');ax.set_xlabel('ΔE od TPN [m] → E');ax.set_ylabel('ΔN od TPN [m] → N');ax.set_title(f'{cid}: okno oględzin z góry; kolor Z')
        fig.colorbar(sc,ax=ax,fraction=.04,pad=.01,label='Z [m]');scale_bar(ax,1)
        # Orthographic view from the catalogued exposure, all ROI points.
        ax=axs[0,1]
        for sid in np.unique(a['PointSourceId'][ii]):
            jj=ii[a['PointSourceId'][ii]==sid];ax.scatter(u[jj],xyz[jj,2],s=8,c=SOURCE_COLORS[int(sid)],linewidths=0)
        ax.scatter(u[li],xyz[li,2],facecolors='none',edgecolors='black',s=20,linewidths=.5)
        ax.set_xlabel(f'Poprzecznie, az {(site["exposure_azimuth_deg"]+90)%360:g}° [m]');ax.set_ylabel('Z [m]');ax.set_title('Rzut od ekspozycji; całe okno, bez zasłaniania');ax.set_ylim(*cfg['plot_z']);ax.set_aspect('equal',adjustable='box');ax.grid(alpha=.2)
        for row,(name,along,cross) in enumerate([('Podłużny',p,u),('Poprzeczny',u,p)]):
            ax=axs[1,row];ix=np.flatnonzero(a['accepted']&(abs(cross)<=.5)&(abs(along)<=4))
            for sid in np.unique(a['PointSourceId'][ix]):
                jj=ix[a['PointSourceId'][ix]==sid];ax.scatter(along[jj],xyz[jj,2],s=12,c=SOURCE_COLORS[int(sid)],linewidths=0)
            ground=ix[a['classification'][ix]==2];ax.scatter(along[ground],xyz[ground,2],s=20,facecolors='none',edgecolors='black',linewidths=.4)
            ax.scatter([0],[m['nearest_xy_record']['Z']],s=45,c=MARK_COLORS['TPN'],edgecolors='black',zorder=9)
            ax.scatter([0],[m['Z']],s=48,c=MARK_COLORS['TPN'],edgecolors='black',marker='X',zorder=9)
            ax.set_xlim(-4,4);ax.set_ylim(*cfg['plot_z']);ax.set_aspect('equal',adjustable='box');ax.grid(alpha=.2);ax.set_xlabel('Odległość od TPN [m]');ax.set_ylabel('Z [m]');ax.set_title(f'{name} przez TPN, szerokość 1 m')
        for k,(l,h) in enumerate(cfg['representative_pairs'],1):
            for typ,i in [('L',l),('U',h)]:
                label=f'{k}{typ}: #{i}'
                for ax,x,y in [(axs[0,0],xyz[i,0]-center[0],xyz[i,1]-center[1]),(axs[0,1],u[i],xyz[i,2])]:
                    ax.scatter([x],[y],s=30,c='white',edgecolors='black',linewidths=1,zorder=10)
                    ax.annotate(label,(x,y),xytext=(6,6 if typ=='U' else -14),textcoords='offset points',fontsize=7,zorder=11,bbox={'facecolor':'white','alpha':.85,'edgecolor':'none'})
        fig.suptitle(f"{site['name']} — {cid}: POTENCJALNA STRUKTURA, otwór i próg niepotwierdzone\nDolna grupa wybrana ręcznym oknem XYZ: {len(li)} odbić; obrys dolnej grupy w górnych panelach",fontsize=13)
        fig.text(.04,.065,'Kolor: PointSourceId 80 niebieski, 81 pomarańczowy, 82 zielony (góra-lewo: Z). Obrys na przekrojach: klasa 2.\nL/U oznacza tylko niższy/wyższy rekord, nie podłogę/strop. Czerwony prostokąt: ręcznie wybrany zakres XY dolnej grupy.',fontsize=8)
        footer(fig,'● umowny XY@Z*; X katalog XYZ datum unknown.');fig.savefig(out/f'{site["slug"]}-candidate.png',dpi=190);plt.close(fig)
        results.append(data)
    write_csv(out/'candidate-near-vertical-pairs.csv',pairs_out);write_csv(out/'candidate-stacked-cells-05m.csv',cellrows)
    return results


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--data-dir',type=Path,default=DEFAULT_DATA);parser.add_argument('--out-dir',type=Path,default=HERE);args=parser.parse_args();out=args.out_dir;out.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.titlepad':10,'savefig.facecolor':'white'})
    manifest=json.loads((HERE.parent/'inspection.json').read_text());report={'settings':SETTINGS,'runtime':{'python':platform.python_version(),'numpy':np.__version__,'matplotlib':matplotlib.__version__,'pyyaml':yaml.__version__},'input_verification':{},'sites':[]}
    for name,expected in manifest.items():
        path=args.data_dir/name;h=sha(path);assert h==expected['sha256'],f'SHA mismatch {name}';assert path.stat().st_size==expected['bytes'];report['input_verification'][name]={'sha256':h,'bytes':path.stat().st_size}
    clouds={};all_markers=[];support=[];spread_rows=[]
    for site in SITES:
        print(f'Inspecting {site["file"]}',flush=True);a=read_las(args.data_dir/site['file']);clouds[site['slug']]=a;assert a['header']['count']==manifest[site['file']]['count'];assert counts(a['classification'])==manifest[site['file']]['class_counts'];assert counts(a['PointSourceId'])==manifest[site['file']]['source_id_counts']
        yp=ROOT/f"data/objects/{site['object'].split('-')[0]}/{site['object']}.yml";yd=yaml.safe_load(yp.read_text());assert yd['id']==site['object'] and yd['cave_id']==site['cave']
        site['yaml']={'path':str(yp.relative_to(ROOT)),'sha256':sha(yp),'best_measurement':yd['best_measurement'],'original_measurements':yd['measurements']}
        site['header']=a['header'];site['counts']={'total':len(a['xyz']),'accepted':int(a['accepted'].sum()),'excluded':int((~a['accepted']).sum()),'classification':counts(a['classification']),'PointSourceId':counts(a['PointSourceId']),'withheld':int(a['withheld'].sum()),'synthetic':int(a['synthetic'].sum()),'keypoint':int(a['keypoint'].sum()),'scan_direction_flag':counts(a['scan_direction_flag']),'edge_of_flight_line':counts(a['edge_of_flight_line'])}
        ms=[];xyz=a['xyz'];origin=xyz[:,:2].min(0)
        for measurement in yd['measurements']:
            m={'object':site['object'],'id':measurement['id'],'source':measurement['source'],'X':measurement['y_1992'],'Y':measurement['x_1992'],'Z':measurement['elevation_m'],'elevation_datum':measurement.get('elevation_datum','unknown')}
            assert m['elevation_datum']=='unknown'
            delta=xyz[:,:2]-[m['X'],m['Y']];d=np.hypot(delta[:,0],delta[:,1]);i=int(np.argmin(np.where(a['accepted'],d,np.inf)));pr=point(a,i);pr.update({'dx_m':float(delta[i,0]),'dy_m':float(delta[i,1]),'distance_xy_m':float(d[i])});m['nearest_xy_record']=pr
            m['display_anchor_unmeasured_xyz']={'X':m['X'],'Y':m['Y'],'Z':pr['Z'],'note':'unmeasured anchor; Z copied from nearest accepted XY point, not terrain interpolation or threshold'}
            support.append({'role':f"{m['object']} {m['source']} actual nearest XY record",**point(a,i)})
            all_markers.append({k:m[k] for k in ['object','id','source','X','Y','Z','elevation_datum']}|{'anchor_X_unmeasured':m['X'],'anchor_Y_unmeasured':m['Y'],'anchor_Z_unmeasured':pr['Z'],'nearest_record_index':i,'nearest_X':pr['X_easting'],'nearest_Y':pr['Y_northing'],'nearest_Z':pr['Z'],'nearest_dx_m':pr['dx_m'],'nearest_dy_m':pr['dy_m'],'nearest_distance_xy_m':pr['distance_xy_m'],'nearest_PointSourceId':pr['PointSourceId'],'nearest_classification':pr['classification']})
            m['radial_diagnostics']=[]
            for radius in SETTINGS['radial_diagnostic_radii_m']:
                mask=a['accepted']&(d<=radius);ix=np.flatnonzero(mask);z=xyz[ix,2]
                m['radial_diagnostics'].append({'radius_m':radius,'count':len(ix),'classification':counts(a['classification'][ix]),'PointSourceId':counts(a['PointSourceId'][ix]),'z_quantiles_0_10_50_90_100':np.quantile(z,[0,.1,.5,.9,1]).tolist() if len(z) else [],'min_z_record_index':int(ix[np.argmin(z)]) if len(z) else None,'max_z_record_index':int(ix[np.argmax(z)]) if len(z) else None})
            m['nearest_xy_by_group']=[]
            for sid in np.unique(a['PointSourceId']):
                for subset in ['accepted','class2']:
                    mask=a['accepted']&(a['PointSourceId']==sid)
                    if subset=='class2':mask&=a['classification']==2
                    if not mask.any():continue
                    j=int(np.argmin(np.where(mask,d,np.inf)));r={'subset':subset,'distance_xy_m':float(d[j]),**point(a,j)};m['nearest_xy_by_group'].append(r)
            # Coverage/vertical-spread diagnostic, never a hole detector.
            for cell in SETTINGS['vertical_spread_xy_cell_sizes_m']:
                near=a['accepted']&(d<=12);ii=np.flatnonzero(near);cells=np.floor((xyz[ii,:2]-origin)/cell).astype(int)
                keys,inv=np.unique(cells,axis=0,return_inverse=True);n=np.bincount(inv);lo=np.full(len(keys),np.inf);hi=np.full(len(keys),-np.inf)
                np.minimum.at(lo,inv,xyz[ii,2]);np.maximum.at(hi,inv,xyz[ii,2])
                valid=np.flatnonzero(n>=SETTINGS['minimum_points_per_spread_cell']);ranked=sorted(valid,key=lambda k:(-(hi[k]-lo[k]),int(keys[k,0]),int(keys[k,1])))[:20]
                for k in ranked:
                    jj=ii[inv==k];l=int(jj[np.argmin(xyz[jj,2])]);h=int(jj[np.argmax(xyz[jj,2])]);cellmin=origin+keys[k]*cell
                    spread_rows.append({'object':m['object'],'source_position':m['source'],'cell_size_m':cell,'cell_Xmin':round(float(cellmin[0]),4),'cell_Ymin':round(float(cellmin[1]),4),'point_count':int(n[k]),'z_min':round(float(lo[k]),2),'z_max':round(float(hi[k]),2),'z_span_m':round(float(hi[k]-lo[k]),2),'min_record_index':l,'max_record_index':h,'PointSourceIds':';'.join(counts(a['PointSourceId'][jj])),'classes':';'.join(counts(a['classification'][jj]))})
            m['sections']=sections(site,a,m,out);ms.append(m)
        site['measurements']=ms
        if len(ms)==2:site['position_separation_xy_m']=math.hypot(ms[0]['X']-ms[1]['X'],ms[0]['Y']-ms[1]['Y'])
        overview(site,a,ms,out)
        if site['slug']=='pod-wanta':panels=[(f"pod-wanta-{m['source'].lower()}",[m],np.array([m['X'],m['Y']])) for m in ms]
        else:panels=[('sniezna',ms,np.mean([[m['X'],m['Y']] for m in ms],axis=0))]
        for slug,markers,center in panels:
            context_figure(site,a,markers,center,slug,out);source_figure(site,a,markers,center,slug,out)
        report['sites'].append(site)
    marker_z_figure(SITES,clouds,out)
    report['candidate_observations']=candidates(SITES,clouds,out,support)
    write_csv(out/'markers.csv',all_markers);write_csv(out/'support-points.csv',support);write_csv(out/'vertical-spread-diagnostic.csv',spread_rows)
    (out/'analysis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=lambda v:int(v) if isinstance(v,np.integer) else float(v) if isinstance(v,np.floating) else str(v))+'\n')
    print(f'Wrote {out}; hashes/counts checked; {len(spread_rows)} diagnostic cells (not cave candidates)',flush=True)

if __name__=='__main__':main()

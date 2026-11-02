"""Compare fixed survey points with unchanged Georeferencer plan geometry."""
import argparse
import copy
import csv
import hashlib
import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import yaml
from PIL import Image
from pyproj import Transformer

parser = argparse.ArgumentParser()
parser.add_argument('--georeferencer', type=Path, required=True)
parser.add_argument('--catalogue', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
geo = args.georeferencer.resolve()
root = args.catalogue.resolve()
out = args.output.resolve()
out.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(geo/'pipeline'))
spec = importlib.util.spec_from_file_location('geo_generator', geo/'pipeline/02_generate_geotiff.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

pin = json.loads((geo/'data/coordinate-source/source.json').read_text())
snapshot = geo/'data/coordinate-source'/pin['snapshot']
assert sha(snapshot) == pin['sha256']
old = {r['object_id']:r for r in csv.DictReader(snapshot.open())}
crs = Transformer.from_crs(4326,2180,always_xy=True)
ids = ['MTW-0013','MTW-0076','MTW-0050','MTW-0016']
new = {}
for i in ids:
    d=yaml.safe_load((root/f'data/objects/{i[:3]}/{i}.yml').read_text())
    m=next(m for m in d['measurements'] if m['id']==d['best_measurement']['measurement_id'])
    new[i]={'E':m['y_1992'],'N':m['x_1992'],'H':m['elevation_m'],'name':d['name_local'],'source_ref':m['source_ref']}

plans={}
fingerprints={str(snapshot.relative_to(geo)):sha(snapshot)}
for pid in ['001478','001548','001549']:
    folder=geo/'data/caves'/pid
    meta=yaml.safe_load((folder/'meta.yaml').read_text())
    resolved=copy.deepcopy(meta)
    obj=meta['coordinates']['gps_kataster_object_id']
    resolved['coordinates']['lat']=float(old[obj]['lat'])
    resolved['coordinates']['lon']=float(old[obj]['lon'])
    p=generator.compute_world_file(resolved)
    M=np.array([[p['A'],p['B']],[p['D'],p['E']]])
    corner=np.array([p['C'],p['F']])-M@np.array([.5,.5])
    entrance=np.array([meta['entrance']['x'],meta['entrance']['y']])
    anchor=np.array(crs.transform(resolved['coordinates']['lon'],resolved['coordinates']['lat']))
    assert np.linalg.norm(M@entrance+corner-anchor)<1e-7
    # Independent reconstruction from the historical direction, current ppm and click.
    hist=generator.orientation.default_context()['plans'][pid]['historical_tfw']['parameters']
    r=math.atan2(hist['D'],hist['A']); mpp=1/meta['scale']['pixels_per_meter']
    independent=mpp*np.array([[math.cos(r),math.sin(r)],[math.sin(r),-math.cos(r)]])
    assert np.max(np.abs(M-independent))<1e-12
    plans[pid]={'meta':meta,'params':p,'M':M,'corner':corner,'entrance':entrance,'anchor':anchor}
    for fn in ['meta.yaml','image.tif','image_original.jpg']:
        fingerprints[str((folder/fn).relative_to(geo))]=sha(folder/fn)
    assert sha(folder/'image.tif')==meta['orientation']['image_sha256']
fingerprints['data/baseline/2026-10-24/catalogue.json']=sha(geo/'data/baseline/2026-10-24/catalogue.json')

def en(i):
    return np.array([new[i]['E'],new[i]['N']])

kozia=plans['001478']
# Manually read the physical entrance triangle, not its numbered circle/arrow.
second_pixel=np.array([3994.,952.])
plan_vector=kozia['M']@(second_pixel-kozia['entrance'])
survey_vector=en('MTW-0076')-en('MTW-0013')
same_residual=float(np.linalg.norm(survey_vector-plan_vector))
reverse_residual=float(np.linalg.norm(-survey_vector-plan_vector))
grzeda_ids=['MTW-0050','MTW-0016']
anchors={i:np.array([float(old[i]['y_1992']),float(old[i]['x_1992'])]) for i in grzeda_ids}
distances={i:{j:float(np.linalg.norm(en(i)-anchors[j])) for j in grzeda_ids} for i in grzeda_ids}
metrics={
 'georeferencer_commit':subprocess.check_output(['git','-C',str(geo),'rev-parse','HEAD'],text=True).strip(),
 'gps_proposal_commit':subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip(),
 'coordinate_pin':pin,'georeferencer_inputs_sha256':fingerprints,
 'source_measurements':new,
 'kozia':{
   'entrance_I_ui_px':kozia['entrance'].tolist(),'entrance_II_ui_px':second_pixel.tolist(),
   'entrance_II_pick_tolerance_px':10,'entrance_II_pick_tolerance_m':10/kozia['meta']['scale']['pixels_per_meter'],
   'plan_vector_E_N_m':plan_vector.tolist(),'survey_vector_E_N_m':survey_vector.tolist(),
   'plan_length_m':float(np.linalg.norm(plan_vector)),'survey_length_m':float(np.linalg.norm(survey_vector)),
   'same_names_vector_residual_m':same_residual,'swapped_names_vector_residual_m':reverse_residual,
   'plan_to_proposed_I_translation_E_N_m':(en('MTW-0013')-kozia['anchor']).tolist(),
   'survey_H_II_minus_I_m':new['MTW-0076']['H']-new['MTW-0013']['H'],
   'PIG_H_II_minus_I_m':-2.8,
   'relative_height_disagreement_m':new['MTW-0076']['H']-new['MTW-0013']['H']+2.8,
   'orientation_status':'unverified; historical_tfw, unchanged',
   'note':'Reanchoring is a diagnostic translation, not independent validation of the anchored point or an approved plan correction.'},
 'grzeda':{
   'distance_matrix_new_to_previous_TPN_m':distances,
   'same_names_sum_distance_m':sum(distances[i][i] for i in grzeda_ids),
   'swapped_names_sum_distance_m':distances['MTW-0050']['MTW-0016']+distances['MTW-0016']['MTW-0050'],
   'survey_N_I_minus_II_m':new['MTW-0050']['N']-new['MTW-0016']['N'],
   'survey_H_I_minus_II_m':new['MTW-0050']['H']-new['MTW-0016']['H'],
   'PIG_H_I_minus_II_m':1926.9-1925.2,
   'swapped_labels_H_I_minus_II_m':new['MTW-0016']['H']-new['MTW-0050']['H'],
   'PIG_N_I_minus_II_description_m':-3.,
   'morphology_discriminator':'PIG I: entrance shaft ~7 m; PIG II: entrance pit ~1.5 m.',
   'note':'Plan anchors use the same TPN points shown in the matrix; this is not a second independent positional measurement.'},
 'transforms':{pid:{'TFW':p['params'],'UI_corner_E_N':p['corner'].tolist(),
                       'anchor_E_N':p['anchor'].tolist(),'entrance_UI':p['entrance'].tolist(),
                       'orientation':p['meta']['orientation']} for pid,p in plans.items()},
}
(out/'overlay-evidence.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2)+'\n')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.transforms import Affine2D
from matplotlib.ticker import ScalarFormatter, MultipleLocator

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.titlesize':12,'figure.facecolor':'white'})
red='#D55E00'; blue='#0072B2'

def background(ax,pid,translation=None,crop=None,alpha=.65):
    p=plans[pid]
    image=Image.open(geo/'data/caves'/pid/'image.tif').convert('L')
    left,top,right,bottom=crop or (0,0,image.width,image.height)
    image=image.crop((left,top,right,bottom))
    c=p['corner']+(np.zeros(2) if translation is None else translation)
    M=p['M']
    tr=Affine2D.from_values(M[0,0],M[1,0],M[0,1],M[1,1],c[0],c[1])
    ax.imshow(image,cmap='gray',vmin=0,vmax=255,origin='upper',
              extent=(left,right,bottom,top),transform=tr+ax.transData,alpha=alpha,interpolation='nearest',zorder=0)

def setup(ax,xlim,ylim,step):
    ax.set_xlim(xlim); ax.set_ylim(ylim); ax.set_aspect('equal')
    ax.set_xlabel('E / Y 1992 [m]'); ax.set_ylabel('N / X 1992 [m]')
    for axis in [ax.xaxis,ax.yaxis]:
        fmt=ScalarFormatter(useOffset=False);fmt.set_scientific(False);axis.set_major_formatter(fmt)
        axis.set_major_locator(MultipleLocator(step))
    ax.grid(color='#777777',alpha=.22,zorder=-1)

def point(ax,i,color,marker,label,offset):
    xy=en(i); ax.scatter(*xy,c=color,marker=marker,s=105,linewidths=2,zorder=5)
    ax.annotate(label,xy=xy,xytext=offset,textcoords='offset points',color=color,fontweight='bold',
                bbox={'facecolor':'white','alpha':.9,'edgecolor':'none','pad':2},zorder=6)

fig,axes=plt.subplots(2,1,figsize=(13,8.5))
for ax,shift,title in [(axes[0],np.zeros(2),'A. Plan zakotwiczony w dotychczasowym GPS/TPN (v1.3.2)'),
                       (axes[1],en('MTW-0013')-kozia['anchor'],'B. Tylko przesunięcie planu do nowego otworu I; skala i obrót zachowane')]:
    background(ax,'001478',shift,crop=(1350,650,4450,1700))
    setup(ax,(566060,566200),(152735,152785),20)
    ax.set_title(title,loc='left')
    point(ax,'MTW-0013',red,'x','Marek: I (zachodni)',(8,-22))
    point(ax,'MTW-0076',blue,'D','Marek: II (wschodni)',(-145,18))
    expected_I=kozia['anchor']+shift
    expected_II=kozia['M']@second_pixel+kozia['corner']+shift
    ax.scatter([expected_I[0],expected_II[0]],[expected_I[1],expected_II[1]],s=130,
               facecolors='none',edgecolors='black',linewidths=1.3,zorder=4)
    ax.plot([expected_I[0],expected_II[0]],[expected_I[1],expected_II[1]],'k--',lw=.8,alpha=.6)
    if ax==axes[0]:
        ax.annotate('Otwory I i II odczytane z planu',expected_II,xytext=(-175,45),textcoords='offset points',
                    arrowprops={'arrowstyle':'->','color':'black'},bbox={'facecolor':'white','edgecolor':'none','alpha':.9})
    else:
        ax.text(.02,.05,f'Wektor planu ≈ {np.linalg.norm(plan_vector):.1f} m; pomiar ≈ {np.linalg.norm(survey_vector):.1f} m. '
                f'Rozbieżność wektora ≈ {same_residual:.1f} m; po zamianie nazw ≈ {reverse_residual:.0f} m.',
                transform=ax.transAxes,bbox={'facecolor':'white','edgecolor':'none','alpha':.95},fontsize=10)
fig.suptitle('Jaskinia Kozia — nowe pomiary zachowują kolejność otworów z planu',fontsize=15,fontweight='bold')
fig.subplots_adjust(left=.08,right=.99,bottom=.15,top=.90,hspace=.38)
fig.text(.5,.025,'Plan: S. Kotarba 1998 / PIG, grafika 983; georeferencja a47c390. Krzyżyk/romb: pomiary Marka 17.10.2026.\n'
         'Orientacja planu nieweryfikowana. Okręgi: wskazane miejsca otworów. Panel B jest porównaniem względnym; nie potwierdza wysokości.',
         ha='center',fontsize=9)
fig.savefig(out/'kozia-overlay.png',dpi=160,bbox_inches='tight');plt.close(fig)

fig=plt.figure(figsize=(14,10))
grid=fig.add_gridspec(2,2,width_ratios=[1.3,1.0],left=.07,right=.98,bottom=.14,top=.92,wspace=.16,hspace=.18)
ax=fig.add_subplot(grid[:,0])
background(ax,'001549',crop=(90,300,2080,1520),alpha=.7)
background(ax,'001548',crop=(260,680,1180,1260),alpha=.7)
setup(ax,(566600,566614),(152817,152830),2)
ax.set_title('Plany w dotychczasowym położeniu GPS/TPN',loc='left')
for i,label,offset in [('MTW-0050','PIG I / stary GPS',(-3,-34)),('MTW-0016','PIG II / stary GPS',(-2,29))]:
    a=anchors[i];ax.scatter(*a,s=180,facecolors='none',edgecolors='black',linewidths=1.5,zorder=3)
    ax.annotate(label,a,xytext=offset,textcoords='offset points',bbox={'facecolor':'white','edgecolor':'none','alpha':.9},zorder=6)
point(ax,'MTW-0050',red,'x','Marek: „I”',(14,-24))
point(ax,'MTW-0016',blue,'D','Marek: „II”',(14,11))
for i,j in [('MTW-0050','MTW-0016'),('MTW-0016','MTW-0050')]:
    ax.plot([en(i)[0],anchors[j][0]],[en(i)[1],anchors[j][1]],'--',color='#555555',lw=1.4)
ax.text(.025,.02,'Przerywane odcinki: wariant zamiany nazw.\n'
        f'Marek „I” → stary II: {distances["MTW-0050"]["MTW-0016"]:.2f} m\n'
        f'Marek „II” → stary I: {distances["MTW-0016"]["MTW-0050"]:.2f} m',
        transform=ax.transAxes,bbox={'facecolor':'white','edgecolor':'none','alpha':.95},fontsize=10,zorder=8)
for sub,pid,title in [(grid[0,1],'001549','PIG I: studnia wejściowa około 7 m'),(grid[1,1],'001548','PIG II: studzienka wejściowa około 1,5 m')]:
    a=fig.add_subplot(sub)
    image=Image.open(geo/'data/caves'/pid/'image_original.jpg').convert('RGB')
    a.imshow(image);a.axis('off');a.set_title(title,loc='left',fontsize=11)
fig.suptitle('Dziury w Grzędzie — położenie wskazuje na zamianę oznaczeń w raporcie',fontsize=15,fontweight='bold')
fig.text(.5,.025,'Źródła planów: M. Kardaś 1978 / PIG, grafiki 1059 i 1058; Georeferencer a47c390, GPS v1.3.2.\n'
         'Po lewej tylko części planowe, bez przekrojów. Po prawej oryginalne rysunki do rozpoznania morfologii.\n'
         'Kotwice planów i stare punkty GPS to te same dane TPN; bliskość i zgodność opisów są poszlaką, nie terenowym dowodem tożsamości.',
         ha='center',fontsize=9)
fig.savefig(out/'grzeda-overlay.png',dpi=160,bbox_inches='tight');plt.close(fig)
print(json.dumps({'kozia':metrics['kozia'],'grzeda':metrics['grzeda']},ensure_ascii=False,indent=2))

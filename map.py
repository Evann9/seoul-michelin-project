import folium
import geopandas as gpd
from folium import CustomIcon
from shapely.geometry import Polygon
import os
import json
from shapely.geometry import shape

# 1. 데이터 로드 함수
def load_geojson(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)
    features = data['features']
    geoms = [shape(f['geometry']) for f in features]
    props = [f['properties'] for f in features]
    return gpd.GeoDataFrame(props, geometry=geoms, crs="EPSG:4326")

print("데이터를 로드 중입니다...")
seoul_map = load_geojson('./data/team_pro_seoul_map_4326.geojson')
michelin_points = load_geojson('./data/team_pro_michelin_point_4326.geojson')

# 설정값
target_districts = ['강남구', '용산구', '중구', '종로구', '송파구', '성동구']
NORMAL_SIZE = 15
HOVER_SIZE = 30
icon_path = './img/11.png' # 마커 이미지 경로

for target_gu in target_districts:
    print(f"'{target_gu}' 고급형 레드 지도 생성 중...")
    
    selected_gu = seoul_map[seoul_map['SIG_KOR_NM'] == target_gu]
    if selected_gu.empty: continue
        
    gu_geom = selected_gu.unary_union
    gu_points = michelin_points[michelin_points.geometry.intersects(gu_geom)]
    
    # 지도 객체 생성
    m = folium.Map(tiles=None, dragging=True, zoom_control=True, scrollWheelZoom=True, attributionControl=False)
    
    # [배경 설정] 미슐랭 레드(#bd1622) 적용
    world_rect = Polygon([(-180, -90), (-180, 90), (180, 90), (180, -90)])
    mask_polygon = world_rect.difference(gu_geom)
    folium.GeoJson(
        mask_polygon, 
        style_function=lambda x: {'fillColor': '#bd1622', 'color': 'none', 'fillOpacity': 1.0}
    ).add_to(m)
    
    # 구 내부 (레드 배경과 대비되도록 밝은 톤)
    folium.GeoJson(
        selected_gu, 
        style_function=lambda x: {'fillColor': '#fdfaf5', 'color': '#ffffff', 'weight': 2, 'fillOpacity': 0.9}
    ).add_to(m)
    
    # Hover CSS
    hover_css = f"""
    <style>
        .leaflet-marker-icon {{ transition: all 0.2s ease-out; z-index: 1000 !important; cursor: pointer; }}
        .leaflet-marker-icon:hover {{
            width: {HOVER_SIZE}px !important; height: {HOVER_SIZE}px !important;
            margin-left: -{HOVER_SIZE/2}px !important; margin-top: -{HOVER_SIZE/2}px !important;
            z-index: 2000 !important; filter: drop-shadow(0 0 5px rgba(0,0,0,0.3));
        }}
    </style>
    """
    m.get_root().header.add_child(folium.Element(hover_css))
    
    # 마커 및 연동 스크립트 추가
    for idx, row in gu_points.iterrows():
        lat, lng = row.geometry.y, row.geometry.x
        if os.path.exists(icon_path):
            icon = CustomIcon(icon_path, icon_size=(NORMAL_SIZE, NORMAL_SIZE))
            marker = folium.Marker(
                location=[lat, lng],
                icon=icon,
                tooltip=folium.Tooltip(row['rest_name'], sticky=True)
            ).add_to(m)
            
            res_name = row['rest_name'].replace("'", "\\'")
            
            # [핵심] 클릭 시 부모 창의 findAndShowRestaurant 호출
            click_script = f"""
                var el = document.querySelector('#{marker.get_name()}');
                if(el) {{
                    el.addEventListener('click', function() {{
                        if (window.parent && typeof window.parent.findAndShowRestaurant === 'function') {{
                            window.parent.findAndShowRestaurant('{res_name}');
                        }}
                    }});
                }}
            """
            m.get_root().script.add_child(folium.Element(click_script))

    bounds = selected_gu.total_bounds.tolist()
    m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]], padding=(0.1, 0.1))
    m.save(f'map_{target_gu}.html')

print("🎉 레드 배경 지도가 모두 생성되었습니다!")
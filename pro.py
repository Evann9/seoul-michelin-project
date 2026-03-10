import folium
import geopandas as gpd
from folium import CustomIcon
from shapely.geometry import Polygon
from shapely.ops import unary_union

# 1. 데이터 로드
seoul_map = gpd.read_file('./data/team_pro_seoul_map_4326.geojson')
michelin_points = gpd.read_file('./data/team_pro_michelin_point_4326.geojson')

# 2. 지도 초기 설정 (배경 제거)
m = folium.Map(
    tiles=None, 
    dragging=False,
    zoom_control=False,
    scrollWheelZoom=False,
    doubleClickZoom=False,
    attributionControl=False
)

# 3. 서울 외 지역 가리는 마스크 생성 (배경 제거)
world_rect = Polygon([(-180, -90), (-180, 90), (180, 90), (180, -90)])
seoul_exterior = unary_union(seoul_map.geometry)
mask_polygon = world_rect.difference(seoul_exterior)

folium.GeoJson(
    mask_polygon,
    style_function=lambda x: {
        'fillColor': '#ffffff', 
        'color': 'none',
        'fillOpacity': 1.0
    }
).add_to(m)

# 4. 서울 자치구 레이어
folium.GeoJson(
    seoul_map,
    style_function=lambda x: {
        'fillColor': '#f8f9fa', 
        'color': '#adb5bd', 
        'weight': 1,
        'fillOpacity': 1.0
    }
).add_to(m)

# 5. [핵심] 식당 위치에 업로드하신 사진 마커 추가
icon_path = './img/11.png' # 업로드하신 파일명

for idx, row in michelin_points.iterrows():
    if row.geometry:
        lng, lat = row.geometry.x, row.geometry.y
        
        # CustomIcon 설정 (크기 4.5)
        icon = CustomIcon(
            icon_path,
            icon_size=(20,20) 
        )
        
        folium.Marker(
            location=[lat, lng],
            icon=icon,
            # 마우스를 올렸을 때 파란 네모가 생기지 않도록 가벼운 팝업만 연결
            popup=folium.Popup(f"<b>{row['rest_name']}</b>", max_width=200)
        ).add_to(m)

# 6. 10% 여백 설정 후 화면 맞춤
min_lng, min_lat, max_lng, max_lat = seoul_map.total_bounds
lng_margin = (max_lng - min_lng) * 0.1
lat_margin = (max_lat - min_lat) * 0.1

m.fit_bounds([
    [min_lat - lat_margin, min_lng - lng_margin],
    [max_lat + lat_margin, max_lng + lng_margin]
])

# 7. 저장
m.save('seoul_michelin_custom_photo_map.html')
print("작업 완료! seoul_michelin_custom_photo_map.html 파일을 확인하세요.")
// ---------------------------------------------------------
// [변수 선언부: 데이터를 담아두는 공용 바구니들]
// ---------------------------------------------------------

let map; // 지도 자체를 담아둘 변수
let geojsonLayer; // 지도의 '구 경계선' 그림을 담아둘 변수
const targetGus = ['강남구', '용산구', '중구', '종로구', '송파구', '성동구']; // 우리가 서비스하는 구 이름들



// [핵심 장바구니] 사용자가 어떤 필터를 클릭했는지 기억해두는 '상태 보따리'입니다.
// 항상 이 보따리 상태를 유지하며 서버에 "이대로 필터링해줘!" 라고 요청합니다.
let selectedFilters = {
    grade: [], 
    cuisine: [], 
    favorite: false, 
    gu: '전체' 
};

let currentRestaurantData = null; // 현재 상세 보기로 열려있는 식당의 정보를 잠시 저장합니다.

// 지도 위 마커(빨간 핀)들을 한데 묶어서 관리하는 바구니입니다. 지우거나 다시 그릴 때 한 번에 제어하기 편합니다.
let markerLayerGroup = L.layerGroup();

let pointData; // 서버에서 받아온 식당들의 '위도, 경도(좌표)' 데이터를 저장해 둘 바구니입니다.

// ---------------------------------------------------------
// [오른쪽 필터 버튼 클릭 센서 달기]
// ---------------------------------------------------------
// 화면에 있는 모든 '.filter-btn'을 찾아서 각각에게 "클릭되면 이 일을 해!"라고 센서를 붙여줍니다.
document.querySelectorAll('.filter-btn').forEach(button => {
    button.addEventListener('click', function() {
        
        // 만약 누른 버튼이 '전체' 버튼이라면, 필터 초기화 함수를 부르고 여기서 끝냅니다.
        if(this.id === 'btn-all') {
            resetFilters();
            return;
        }

        // 다른 버튼을 눌렀으니 '전체' 버튼의 활성화(빨간색)를 끕니다.
        document.getElementById('btn-all').classList.remove('active');
        
        // 내가 방금 누른 버튼의 색상을 켰다 껐다(toggle) 합니다.
        this.classList.toggle('active');

        // 이 버튼에 숨겨진 꼬리표(category, value)를 읽어옵니다. (예: grade, 3 Stars)
        const category = this.getAttribute('data-category');
        const value = this.getAttribute('data-value');

        // 읽어온 정보에 따라 우리의 '공용 장바구니(selectedFilters)' 내용을 업데이트합니다.
        if(category === 'favorite') {
            // 찜 버튼은 켜졌는지(true) 꺼졌는지(false)만 판단합니다.
            selectedFilters.favorite = this.classList.contains('active');
        } else if (category === 'grade') {
            if (this.classList.contains('active')) {
                // 켜졌으면 바구니 배열(push)에 넣고
                selectedFilters.grade.push(value);
            } else {
                // 꺼졌으면 바구니에서 그 값만 쏙 빼서 버립니다(filter).
                selectedFilters.grade = selectedFilters.grade.filter(v => v !== value);
            }
        }
        
        // 바뀐 장바구니 내용으로 태그 모양을 다시 그리고, 서버에 새로운 리스트를 요청합니다.
        updateFilterTags();
        fetchRestaurantsFromServer();
    });
});

// ---------------------------------------------------------
// [지도 그리기 세트 (초기화 및 데이터 로드)]
// ---------------------------------------------------------

// 지도를 처음 화면에 띄우는 함수입니다. (window.onload 때 실행됨)
async function initMap() {
    // Leaflet 엔진에게 "id가 'map'인 곳에 서울 중심(37.5665, 126.9780)으로 줌 레벨 11로 지도를 그려줘!"라고 명령합니다.
    map = L.map('map', { 
        zoomControl: false, 
        attributionControl: false 
    }).setView([37.5665, 126.9780], 11);
    
    // await: "지도 데이터를 다 가져올 때까지 여기서 꼼짝 말고 기다려!"라는 뜻입니다.
    await loadMapData(); 
}

// 지도의 '구 경계선'과 '마커(점)' 데이터를 서버에서 가져와 지도에 덮어씌우는 공장입니다.
async function loadMapData() {
    try {
        // 1. 서울시 구 경계선(다각형) 파일을 가져옵니다.
        const mapRes = await fetch('/static/GeoJSON/team_pro_seoul_map_4326.geojson');
        const mapData = await mapRes.json();

        // 가져온 선 데이터에 미슐랭 색깔과 호버(마우스 올림) 효과를 설정합니다.
        geojsonLayer = L.geoJson(mapData, {
            style: (feature) => {
                const isTarget = targetGus.includes(feature.properties.SIG_KOR_NM);
                return {
                    fillColor: '#fdfaf5', // 크림색
                    color: '#7d373a',     // 테두리 빨간색
                    weight: 1.2, 
                    fillOpacity: isTarget ? 1 : 0.9
                };
            },
            onEachFeature: (feature, layer) => {
                const guName = feature.properties.SIG_KOR_NM;
                
                // 우리가 관리하는 구일 때만 마우스 반응을 추가합니다.
                if (targetGus.includes(guName)) {
                    layer.on({
                        mouseover: (e) => { e.target.setStyle({ fillColor: '#ffffff', weight: 2.5 }); }, // 하얗게 빛남
                        mouseout: (e) => { e.target.setStyle({ fillColor: '#fdfaf5', weight: 1.2 }); }, // 원래대로
                        click: (e) => {
                            // 지도의 '구'를 클릭하면, 상단의 구 버튼을 찾아서 대신 누른 것처럼 작동시킵니다.
                            const guName = feature.properties.SIG_KOR_NM;
                            const btn = Array.from(document.querySelectorAll('.gu-btn')).find(b => b.innerText === guName);
                            focusDistrict(guName, btn);
                        }
                    });
                }
            }
        }).addTo(map); // 완성된 경계선을 지도에 올립니다.

        // 2. 식당 위치(점) 파일을 가져와서 전역 바구니(pointData)에 보관합니다.
        const pointRes = await fetch('/static/GeoJSON/team_pro_michelin_point_4326.geojson');
        pointData = await pointRes.json();

        // 처음에는 필터 없이 '전체' 마커를 모두 화면에 그립니다.
        displayMarkers('전체');

    } catch (e) {
        console.error("지도 로딩 실패:", e);
    }
}

// 특정 조건(구 이름 등)에 맞는 마커만 골라서 지도에 찍어주는 함수입니다.
function displayMarkers(guName) {
    // 1. 기존에 찍혀있던 핀들을 싹 뽑아버립니다 (지우개 역할).
    markerLayerGroup.clearLayers();

    // 2. 아까 저장해둔 좌표 보따리(pointData)를 하나씩 뒤지면서 조건에 맞는 애들만 핀을 꽂습니다.
    L.geoJson(pointData, {
        // filter: 마커를 그릴지 말지 O,X 퀴즈를 내는 곳입니다.
        filter: (feature) => {
            if (guName === '전체') return true; // 전체면 무조건 합격(true)!
            // 속성 데이터 중 'addr(주소)'에 클릭한 구 이름(예: 강남구)이 포함되어 있으면 합격!
            return feature.properties['addr'] === guName || feature.properties['addr'].includes(guName);
        },
        // 합격한 녀석들만 이 안으로 들어와 진짜 마커(이미지)로 변신합니다.
        pointToLayer: (feature, latlng) => {
            const icon = L.icon({ iconUrl: '/static/img/logo.png', iconSize: [25, 25] });
            const marker = L.marker(latlng, { icon: icon });
            const resName = feature.properties["name"] || feature.properties['레스토'] || "정보 없음";

            // [마커 클릭 이벤트] 마커를 누르면 상세 창이 열리도록 설정합니다.
            marker.on('click', () => {
                // 전체 데이터(restaurantsData)에서 이 마커의 이름과 똑같은 녀석의 전체 정보를 찾습니다.
                const resInfo = restaurantsData.find(r => r.name === resName);
                if (resInfo) {
                    // 상세창이 이해할 수 있는 꼬리표(이름표)로 예쁘게 번역해서 포장합니다.
                    const translatedInfo = {
                        restaurant_id: resInfo.restaurant_id,
                        restaurant_name: resInfo.name,
                        address: resInfo.addr,
                        grade: resInfo.star,
                        cuisine_type: resInfo.cuisine,
                        price: resInfo.price,
                        is_favorite: resInfo.is_favorite,
                        img_folder: resInfo.img_folder
                    };
                    // 포장한 데이터를 암호화(인코딩)해서 상세창 함수로 던져줍니다.
                    showDetail(encodeURIComponent(JSON.stringify(translatedInfo)));
                }
            });

            // 마커에 마우스를 올렸을 때 식당 이름이 뜨는 툴팁 달기
            marker.bindTooltip(resName, { direction: 'top', className: 'custom-tooltip' });
            return marker; // 완성된 마커 반환!
        }
    }).addTo(markerLayerGroup); // 반환된 마커들을 그룹 바구니에 차곡차곡 담습니다.

    // 3. 핀이 가득 담긴 그룹 바구니를 지도 위에 철퍼덕 얹습니다.
    markerLayerGroup.addTo(map);
}

// ---------------------------------------------------------
// [필터 연동 핵심 로직: 구 이동 및 다중 필터링]
// ---------------------------------------------------------

// 지도를 이동시키고 필터를 갱신하는 가장 중요한 함수입니다.
function focusDistrict(guName, btn) {
    // 1. 모든 구 버튼의 색깔을 빼고, 방금 누른 버튼만 빨갛게 칠합니다.
    document.querySelectorAll('.gu-btn').forEach(b => b.classList.remove('active'));
    if(btn) btn.classList.add('active');

    // 2. [가장 중요] 전역 장바구니의 'gu' 항목을 내가 누른 구 이름으로 갈아 끼웁니다.
    selectedFilters.gu = guName;

    // 3. 지도를 스무스하게 이동시키는 줌(Zoom) 로직
    if (guName !== '전체') {
        geojsonLayer.eachLayer(layer => {
            // 구 경계선 데이터를 훑으며 내가 클릭한 구를 찾으면 거기로 화면을 맞춥니다 (fitBounds).
            if (layer.feature.properties.SIG_KOR_NM === guName) {
                map.fitBounds(layer.getBounds(), { padding: [50, 50] });
            }
        });

        // 마커도 해당 구 마커만 남깁니다.
        displayMarkers(guName);

        // 리스트도 해당 구 데이터만 남겨서 새로 그립니다. (단순 구 필터링 전용 임시 로직)
        const filtered = restaurantsData.filter(res => res.gu === guName)
            .map(res => ({
                restaurant_id: res.restaurant_id,
                restaurant_name: res.name,
                address: res.addr,
                grade: res.star.replace(' Stars', '').replace(' Star', ''), 
                cuisine_type: res.cuisine,
                price: res.price,
                is_favorite: res.is_favorite
            }));
        drawList(filtered);

    } else {
        // '전체'를 눌렀을 때는 서울시 전체가 보이게 줌 아웃 하고 원상 복구합니다.
        const allTranslated = restaurantsData.map(res => ({
            restaurant_id: res.restaurant_id,
            restaurant_name: res.name,
            address: res.addr,
            grade: res.star,
            cuisine_type: res.cuisine,
            price: res.price
        }));
        map.setView([37.5665, 126.9780], 11);
        displayMarkers('전체');
        drawList(allTranslated);
    }
    
    // 4. 장바구니 내용이 바뀌었으니, 서버에 전체 필터링을 다시 요청합니다.
    fetchRestaurantsFromServer();
}

// 웹페이지가 켜지면(onload) 제일 처음 자동으로 실행되는 두 개의 명령입니다.
window.onload = function() {
    initMap(); // 1. 지도 켜기
    fetchRestaurantsFromServer(); // 2. 서버에서 식당 데이터 가져와서 리스트 그리기
};

// 음식 체크박스를 누를 때마다 장바구니를 업데이트하는 함수입니다.
function updateCuisineFilter() {
    document.getElementById('btn-all').classList.remove('active'); // 전체 버튼 해제
    
    // 화면에 있는 체크박스 중 '체크된(checked)' 녀석들의 글자(value)만 쏙쏙 뽑아옵니다.
    const checkedBoxes = document.querySelectorAll('#cuisine-checkboxes input[type="checkbox"]:checked');
    selectedFilters.cuisine = Array.from(checkedBoxes).map(cb => cb.value);

    updateFilterTags(); // 눈에 보이는 태그 업데이트
    fetchRestaurantsFromServer(); // 서버에 새 리스트 요청!
}

// 내가 선택한 필터들을 작은 '태그(꼬리표)' 모양으로 화면에 예쁘게 달아주는 함수입니다.
function updateFilterTags() {
    const display = document.getElementById('active-filters-display');
    display.innerHTML = ''; // 싹 지우고 다시 그립니다.

    // 장바구니에 담긴 별점, 음식, 찜 정보를 하나씩 꺼내서 <div> 뱃지로 만듭니다.
    selectedFilters.grade.forEach(g => {
        display.innerHTML += `<div class="filter-tag">${g} Star <span onclick="removeFilter('grade', '${g}')">✖</span></div>`;
    });
    selectedFilters.cuisine.forEach(c => {
        display.innerHTML += `<div class="filter-tag">${c} <span onclick="removeFilter('cuisine', '${c}')">✖</span></div>`;
    });
    if(selectedFilters.favorite) {
        display.innerHTML += `<div class="filter-tag">⭐ 찜한 식당 <span onclick="removeFilter('favorite', '')">✖</span></div>`;
    }

    // 아무것도 선택 안 했으면 다시 '전체' 버튼을 빨갛게 켭니다.
    if(selectedFilters.grade.length === 0 && selectedFilters.cuisine.length === 0 && !selectedFilters.favorite) {
        document.getElementById('btn-all').classList.add('active');
    }
}

// X 버튼을 눌러서 특정 필터를 장바구니에서 빼버리는 함수입니다.
function removeFilter(category, value) {
    if(category === 'grade') {
        selectedFilters.grade = selectedFilters.grade.filter(v => v !== value);
        document.querySelector(`.filter-btn[data-value="${value}"]`).classList.remove('active');
    } else if (category === 'cuisine') {
        selectedFilters.cuisine = selectedFilters.cuisine.filter(v => v !== value);
        document.querySelector(`#cuisine-checkboxes input[value="${value}"]`).checked = false;
    } else if (category === 'favorite') {
        selectedFilters.favorite = false;
        document.querySelector(`.filter-btn[data-category="favorite"]`).classList.remove('active');
    }
    
    updateFilterTags();
    fetchRestaurantsFromServer();
}

// '전체' 버튼을 누르면 장바구니를 싹 비우고 완전 초기화하는 함수입니다.
function resetFilters() {
    selectedFilters = { grade: [], cuisine: [], favorite: false }; // 바구니 텅텅!
    document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
    document.getElementById('btn-all').classList.add('active');
    document.querySelectorAll('#cuisine-checkboxes input[type="checkbox"]').forEach(cb => cb.checked = false);
    updateFilterTags();
    fetchRestaurantsFromServer(); // 비운 바구니로 서버에 다시 요청!
}

// ---------------------------------------------------------
// [서버 통신부: 서버에 심부름꾼 보내기 (Fetch)]
// ---------------------------------------------------------

// 우리의 '장바구니(selectedFilters)'를 들고 서버(app.py)로 가서 데이터(리스트)를 받아오는 핵심 심부름꾼입니다.
function fetchRestaurantsFromServer() {
    fetch('http://127.0.0.1:5000/api/filter', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(selectedFilters) // 장바구니 전체를 포장해서 보냅니다.
    })
    .then(response => response.json()) // 서버가 준 대답을 JSON(자바스크립트 사전)으로 해석합니다.
    .then(data => {
        // 서버에서 '합격자 명단'이 돌아오면 두 가지 일을 시킵니다.
        drawList(data); // 1. 오른쪽 리스트 새로 그리기
        displayMarkersByList(data); // 2. 지도 마커 새로 그리기 (주의: display 오타가 남아있는 상태의 코드입니다)
    })
    .catch(error => console.error('에러:', error)); // 가다가 넘어지면(에러) 콘솔에 빨간 글씨로 띄웁니다.
}

// 서버에서 받아온 '합격자 명단(filteredList)'을 기준으로 지도 위의 마커만 남기는 함수입니다.
function displayMarkersByList(filteredList) {
    markerLayerGroup.clearLayers();

    // 검색 속도를 높이기 위해 합격한 식당들의 '이름'만 따로 모아 배열(allowedNames)로 만듭니다.
    const allowedNames = filteredList.map(res => res.restaurant_name || res.name);

    // 전체 좌표 보따리(pointData)를 훑으면서...
    L.geoJson(pointData, {
        filter: (feature) => {
            const resName = feature.properties.name || feature.properties.레스토 || "";
            // 이 식당 이름이 아까 만든 '합격자 이름 명단'에 들어있으면 지도에 그려라(true)!
            return allowedNames.includes(resName);
        },
        pointToLayer: (feature, latlng) => {
            // 합격한 마커를 생성하는 기존 로직과 동일합니다.
            const icon = L.icon({ iconUrl: '/static/img/logo.png', iconSize: [25, 25] });
            const marker = L.marker(latlng, { icon: icon });
            const resName = feature.properties.name || feature.properties.레스토 || "정보 없음";

            marker.on('click', () => {
                const resInfo = restaurantsData.find(r => r.name === resName);
                if (resInfo) {
                    const translated = {
                        restaurant_id: resInfo.restaurant_id,
                        restaurant_name: resInfo.name,
                        address: resInfo.addr,
                        grade: resInfo.star,
                        cuisine_type: resInfo.cuisine,
                        price: resInfo.price,
                        is_favorite: resInfo.is_favorite,
                        img_folder: resInfo.img_folder || resInfo.name
                    };
                    showDetail(encodeURIComponent(JSON.stringify(translated)));
                }
            });

            marker.bindTooltip(resName, { direction: 'top', className: 'custom-tooltip' });
            return marker;
        }
    }).addTo(markerLayerGroup);

    markerLayerGroup.addTo(map);
}

// ---------------------------------------------------------
// [화면 그리기 공장 (Rendering UI)]
// ---------------------------------------------------------

// 서버에서 받은 데이터를 바탕으로 오른쪽 화면에 하얀 '식당 카드'들을 쭉 만들어 붙이는 공장입니다.
function drawList(restaurants) {
    const listContainer = document.getElementById('restaurant-list');
    listContainer.innerHTML = ''; // 일단 기존 카드들을 싹 청소합니다.

    // 1. 서버 쪽에서 에러가 났을 때(파이썬 에러) 화면에 빨간 경고창을 띄워주는 방어막입니다.
    if (restaurants.error) {
        listContainer.innerHTML = `<p style="color:red; text-align:center;">🚫 ${restaurants.error}<br>터미널(콘솔)을 확인해 주세요.</p>`;
        return;
    }

    // 2. 검색 조건이 빡빡해서 남은 식당이 하나도 없을 때 보여주는 안내 문구입니다.
    if (!Array.isArray(restaurants) || restaurants.length === 0) {
        listContainer.innerHTML = '<p style="color:#777; text-align:center;">조건에 맞는 식당이 없습니다.</p>';
        return;
    }

    // 3. 데이터가 잘 왔다면, 식당(res)을 하나하나 꺼내서 카드를 만듭니다.
    restaurants.forEach(res => {
        const heartIcon = res.is_favorite === 1 ? '⭐' : '☆'; // 1이면 빨간 하트, 아니면 빈 하트
        
        // 나중에 카드를 눌렀을 때 데이터를 넘겨주기 위해 전체 데이터를 예쁘게 접어둡니다(stringify).
        const resDataStr = encodeURIComponent(JSON.stringify(res));

        // HTML 카드 디자인 틀에다가 데이터를 쏙쏙 끼워 넣습니다.
        const card = `
            <div class="restaurant-card" onclick="showDetail('${resDataStr}')">
                <div class="card-favorite-icon" onclick="event.stopPropagation(); toggleFavorite(${res.restaurant_id}, this)">${heartIcon}</div>
                <p style="font-size: 1.2rem; font-weight: bold; margin: 0 0 5px 0;">${res.restaurant_name}</p>
                <p style="font-size: 0.9rem; color: #777; margin: 0;">${res.address} | ${res.cuisine_type}</p>
                <p style="color: #a21927; font-weight: bold; margin-top:5px;">${res.grade}</p>
            </div>
        `;
        // 완성된 카드를 화면에 찍어냅니다.
        listContainer.innerHTML += card;
    });
}

// 특정 식당 카드를 눌렀을 때, 화면 왼쪽에서 상세 정보 창이 튀어나오게 하는 마법 주문입니다.
function showDetail(encodedResData) {
    // 접혀있던 데이터를 다시 펼칩니다(parse).
    const res = JSON.parse(decodeURIComponent(encodedResData));
    const folderName = res.img_folder || res.restaurant_name;
    const imageUrls = [
        `/static/img/${folderName}/image_1.jpg`,
        `/static/img/${folderName}/image_2.jpg`,
        `/static/img/${folderName}/image_3.jpg`,
    ];
    const imgContainer = document.getElementById('detail-images');
    imgContainer.innerHTML = '';

    imageUrls.forEach(url => {
        const imgTag = document.createElement('img');
        imgTag.src = url;
        imgContainer.appendChild(imgTag);
        // 1. 가로 크기 기본 설정
        // 여백(gap) 2% 두 군데(4%)를 제외한 96%를 3등분하여 약 32%씩 가져갑니다.
        imgTag.style.width = "32%"; 
        
        // 2. 높이: 고정 px 대신 가로 길이에 맞춘 '정사각형' 비율 유지
        // [핵심] 이렇게 해야 창이 좁아져서 가로가 줄어들 때 높이도 '함께' 줄어들어 스크롤이 안 생깁니다!
        imgTag.style.aspectRatio = "1 / 1"; 
        
        // 3. 유연함의 최고봉: 자리가 모자라면 한계까지 작아져라!
        imgTag.style.flexShrink = "1"; // 공간 부족 시 축소 허용
        imgTag.style.minWidth = "0";    // [중요] 최소 크기 제한을 없애야 끝까지 줄어듭니다.
        
        // 4. 이미지 자체 비율 유지 및 둥근 모서리
        imgTag.style.objectFit = "cover"; // 찌그러짐 방지
        imgTag.style.borderRadius = "8px";
    });

    currentRestaurantData = res; // 나중에 예약할 때 쓰기 위해 주인공 정보를 전역에 저장합니다.
    
    document.getElementById('map').style.display = 'none'; // 상세창을 위해 지도를 잠깐 숨깁니다.
    
    // 상세창에 '.active' 이름표를 붙여서 화면 밖에서 안으로 스르륵 들어오게 합니다!
    document.getElementById('detail-view').classList.add('active');
    // 지도 위의 구 필터 바는 위로 도망가게 숨깁니다.
    document.getElementById('gu-filter-bar').classList.add('hide');
    
    // 상세창 안의 제목, 주소, 별점 칸에 글씨를 채워 넣습니다.
    document.getElementById("dt-name").innerText = res.restaurant_name;
    document.getElementById('dt-info').innerText = `${res.address} | ${res.cuisine_type}`;
    document.getElementById('dt-stars').innerText = `${res.grade}`;
    document.getElementById('dt-desc').innerText = "평균 가격대: ₩ " + res.price + '~';

    const heartBtn = document.getElementById('detail-favorite-btn');
    heartBtn.innerText = res.is_favorite === 1 ? '⭐' : '☆';
}

// "지도로 돌아가기" 버튼을 누르면 상세창을 닫고 다시 지도를 켜는 함수입니다.
function showMap() {
    document.getElementById('detail-view').classList.remove('active'); // 상세창 퇴장
    document.getElementById('map').style.display = 'flex'; // 지도 다시 등장
    document.getElementById('gu-filter-bar').classList.remove('hide'); // 구 필터 바 다시 하강
}

// ---------------------------------------------------------
// [부가 기능들: 찜하기, 예약하기, 관리자 모드]
// ---------------------------------------------------------

// 1. 하트를 누르면 서버 DB에 "이 식당 찜할게!"라고 알리고 하트 색을 바꾸는 기능입니다.
function toggleFavorite(resId, element) {
    fetch('http://127.0.0.1:5000/api/toggle_favorite', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ restaurant_id: resId })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            // 서버가 성공했다고 하면 하트를 토글(전환)해줍니다.
            element.innerText = data.action === 'added' ? '⭐' : '☆';
        }
    });
}

// (상세 페이지 안에서 하트 눌렀을 때 동작하는 전용 함수입니다.)
function toggleFavoriteFromDetail() {
    if(!currentRestaurantData) return;
    fetch('http://127.0.0.1:5000/api/toggle_favorite', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ restaurant_id: currentRestaurantData.restaurant_id })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            const btn = document.getElementById('detail-favorite-btn');
            btn.innerText = data.action === 'added' ? '⭐' : '☆';
            fetchRestaurantsFromServer(); // 리스트에도 바뀐 하트를 즉시 반영하기 위해 새로고침!
        }
    });
}

// ---------------------------------------------------------
// [예약 시스템 로직]
// ---------------------------------------------------------

// 우리가 서비스할 기준 시간표 (숫자 ID와 실제 화면에 보일 글자)
const timeConfig = {
    1: "18:00",
    2: "19:00",
    3: "20:00",
    4: "21:00"
};

// 예약하기 창을 여는 순간, 서버에 "어떤 시간대가 남았어?"라고 물어보고 버튼을 생성합니다.
async function openReservationModal() {
    if (!currentRestaurantData) return;
    const resId = currentRestaurantData.restaurant_id;
    const container = document.getElementById('time-slot-container');
    const hiddenInput = document.getElementById('selected-time-value');
    
    hiddenInput.value = '';   // 이전에 골라뒀던 시간 초기화

    try {
        // 1. 대기(await)! 서버에서 이미 예약된 시간 목록(예: [1, 3])을 가져올 때까지 기다립니다.
        const response = await fetch(`http://127.0.0.1:5000/api/check_reservation?id=${resId}`);
        const bookedTimes = await response.json();

        // 2. 눈에 보이지 않는 허공의 바구니(DocumentFragment)를 하나 만듭니다. (성능 최적화용)
        const tempFragment = document.createDocumentFragment();
        
        // 3. 시간표(timeConfig)를 하나씩 순회하면서 버튼 4개를 공장처럼 찍어냅니다.
        for (let key in timeConfig) {
            const btn = document.createElement('button');
            btn.type = "button";
            btn.classList.add('time-btn');  // 호버(CSS) 효과 달아주기
            btn.innerText = timeConfig[key]; // "18:00" 글씨 새기기
            
            // 버튼 기본 디자인 세팅
            btn.style.padding = "10px";
            btn.style.border = "1px solid #ddd";
            btn.style.borderRadius = "5px";
            btn.style.backgroundColor = "white";
            btn.style.cursor = "pointer";
            btn.style.color = "black"

            // 이 시간이 서버에서 받은 '이미 예약된 목록'에 들어있는지 확인!
            const isBooked = bookedTimes.includes(parseInt(key));

            if (isBooked) {
                // 예약이 꽉 찼다면: 회색으로 칠하고 클릭 불가(disabled)로 만듭니다.
                btn.disabled = true;
                btn.style.color = "#ccc";
                btn.style.backgroundColor = "#f9f9f9";
                btn.style.cursor = "not-allowed";
                btn.innerText += " (불가)";
            } else {
                // 예약이 가능하다면: 클릭했을 때 빨간색으로 빛나게 이벤트를 달아줍니다.
                btn.onclick = function() {
                    // 일단 모든 버튼을 하얀색으로 원상복구 시킨 뒤에...
                    Array.from(container.children).forEach(b => {
                        if(!b.disabled) {
                            b.style.backgroundColor = "white";
                            b.style.color = "black";
                            b.style.borderColor = "#ddd";
                        }
                    });
                    // 방금 내가 누른 녀석만 빨간색 미슐랭 옷으로 갈아입힙니다!
                    btn.style.backgroundColor = "#a21927";
                    btn.style.color = "white";
                    btn.style.borderColor = "#a21927";
                    
                    // 선택한 시간(예: '1')을 몰래 주머니(hiddenInput)에 저장해둡니다. (나중에 서버에 보낼 용도)
                    hiddenInput.value = key;
                };
            }
            tempFragment.appendChild(btn); // 허공 바구니에 완성된 버튼을 쏙 담습니다.
        }
        
        // 4. 기존 창에 있던 헌 버튼들을 싹 밀어버리고, 허공 바구니에 담은 새 버튼 4개를 한방에 쏟아 붓습니다!
        container.innerHTML = ''; 
        container.appendChild(tempFragment);
        
        // 5. 모든 세팅이 끝나면, 짠! 하고 모달창을 화면에 보여줍니다 (display: flex).
        document.getElementById('reservation-modal').style.display = 'flex';
    
    } catch (error) {
        console.error("데이터 로딩 실패:", error);
        alert("예약 정보를 불러오지 못했습니다.");
    }
}

// 예약 모달창을 닫는(숨기는) 함수입니다.
function closeModal() {
    document.getElementById('reservation-modal').style.display = 'none';
}

// 사용자가 정보를 다 쓰고 "예약 확정"을 눌렀을 때, 그 정보를 포장해서 서버(DB)로 택배를 보내는 함수입니다.
// isForced: 다른 식당 예약이 있을 때 "무시하고 덮어써!"라고 강제 명령할지 여부(기본은 false).
function submitReservation(isForced = false) {
    // 사용자가 입력칸에 적은 이름, 폰번호, 그리고 아까 버튼 눌러서 저장해둔 시간값을 가져옵니다.
    const name = document.getElementById("res-name").value;
    const phone = document.getElementById('res-phone').value;
    const time = document.getElementById('selected-time-value').value; 

    const timeLabel = timeConfig[time];

    // 1. 필수값이 하나라도 비어있으면 빠꾸먹입니다!
    if(!name || !phone || !time) {
        alert("정보를 모두 입력하고 시간을 선택해주세요.");
        return;
    }

    // 2. 전화번호에 한글이나 영어 등 이상한 값이 없는지 정규식(Regex)으로 철저히 검사합니다.
    const phoneRegex = /^[0-9-]{10,13}$/; // 숫자와 하이픈(-)만 허용, 10~13글자 길이 제한
    if (!phoneRegex.test(phone)) {
        alert("유효한 전화번호를 입력해주세요. (예: 010-0000-0000)");
        return;
    }

    // 3. 검사를 통과했다면, 짐을 예쁘게 싸서 서버의 /api/make_reservation 주소로 로켓 배송합니다!
    fetch('http://127.0.0.1:5000/api/make_reservation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            restaurant_id: currentRestaurantData.restaurant_id,
            user_name: name,
            user_phone: phone,
            time: time,
            force: isForced // 서버야, 이거 강제 예약이니? 아니면 그냥 예약이니?
        })
    })
    .then(res => res.json())
    .then(data => {
        // 서버가 편지를 뜯어보고 다양한 상황(status/type)에 맞춰 답장을 보내옵니다.
        
        if (data.success === true) {
            // [상황 1] 깔끔하게 예약 성공! 축하 팝업을 띄웁니다.
            document.getElementById('reservation-modal').style.display = 'none';
            const msg = `<strong>${name}님</strong>, <br>${timeLabel} 예약이 확정되었습니다!`;
            document.getElementById('success-message').innerHTML = msg;
            document.getElementById('success-modal').style.display = 'flex';
        } 
        else if (data.status === "confirm") {
            // [상황 2] "어? 손님 다른 식당에 이 시간에 이미 예약이 있으신데요? 덮어쓸까요?"
            if (confirm(data.message)) {
                // 확인(OK)을 누르면, 아까 이 함수를 다시 부르면서 isForced에 'true' 깃발을 꽂아 보냅니다!
                submitReservation(true); 
            }
        }
        else if (data.type === "ALREADY_BOOKED_HERE") {
            // [상황 3] "이 식당, 이 시간에 이미 당신 예약이 있는데요?" -> 얄짤없이 튕겨냅니다.
            alert(data.message);
        }
        else if (data.type === "USER_MISMATCH") {
            // [상황 4] 누가 이미 가로챘거나, 번호가 틀렸을 때 경고!
            alert("⚠️ " + data.message);
        }                
        else {
            // 그 외 알 수 없는 인터넷/서버 폭발 에러
            alert("예약에 실패했습니다: " + (data.message || "알 수 없는 오류"));
        }                
    })
    .catch(err => console.error("오류 발생:", err));
}

// 성공 모달창의 '확인'을 누르면 창을 숨기는 함수입니다.
function closeSuccessModal() {
    document.getElementById('success-modal').style.display = 'none';
}

// 내 예약을 취소하고 싶을 때 실행되는 함수입니다. 
function cancelReservation() {
    const name = document.getElementById("res-name").value;
    const phone = document.getElementById('res-phone').value;

    if (!name || !phone) {
        alert("❗ 취소하실 예약의 예약자 성함과 번호를 입력해 주세요.");
        return;
    }

    // 진짜 지울 건지(confirm) 한 번 더 무서운 팝업으로 물어봅니다.
    if (!confirm(`[확인] ${name}님, 예약을 정말 취소하시겠습니까?`)) return;
    
    // 삭제(cancel) API로 짐을 꾸려서 보냅니다.
    fetch('http://127.0.0.1:5000/api/cancel_reservation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            restaurant_id: currentRestaurantData.restaurant_id,
            user_name: name,
            user_phone: phone
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert("✨ " + data.message);
            closeModal(); 
            openReservationModal(); // 대박! 취소하자마자 버튼 색깔을 원래대로 실시간 복구시킵니다.
        } else {
            alert("⚠️ 취소 실패: " + data.message); // 정보가 안 맞으면 실패.
        }
    })
    .catch(err => console.error("오류:", err));
}


// "예약 초기화" 버튼: 튜토리얼이나 테스트를 위해 DB를 싹 날려버리는 강력한 리셋 스위치입니다.
document.getElementById('reset-res-btn').addEventListener('click', function() {
    if (confirm("정말로 모든 예약 내역을 초기화하시겠습니까? 이 작업은 되돌릴 수 없습니다.")) {
        fetch('/api/reset_reservations', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert("예약 테이블이 성공적으로 초기화되었습니다.");
                location.reload(); // 성공하면 웹 브라우저를 강제로 새로고침(F5) 시킵니다.
            } else {
                alert("초기화 실패: " + data.message);
            }
        })
        .catch(error => console.error('Error:', error));
    }
});

// "관리자 모드" 버튼: 숨겨진 모든 예약 내역의 장부를 훔쳐보는 은밀한 뒷구멍입니다.
async function openAdmin() {
    // prompt는 사용자에게 텍스트를 입력받는 간단한 팝업입니다.
    const pw = prompt("관리자 비밀번호를 입력하세요.");
    if (pw !== "1234") { 
        alert("비밀번호가 틀렸습니다.");
        return; // 비번 틀리면 함수를 여기서 즉시 강제 종료!
    }

    // 비번을 통과하면 서버에서 장부(DB)를 몰래 긁어옵니다.
    const response = await fetch('http://127.0.0.1:5000/api/admin_reservations');
    const data = await response.json();

    const tbody = document.getElementById('admin-table-body');
    tbody.innerHTML = ''; // 테이블 싹 비우기

    // 긁어온 장부 데이터를 표 형식(<tr>: 한 줄, <td>: 한 칸)으로 아름답게 포장해서 밀어 넣습니다.
    data.forEach(row => {
        tbody.innerHTML += `
            <tr>
                <td>${row.restaurant_name}</td>
                <td>${row.user_name}</td>
                <td>${row.user_phone}</td>
                <td>${timeConfig[row.reservation_time]}</td>
            </tr>
        `;
    });

    // 포장 완료된 장부 모달을 화면에 띄웁니다!
    document.getElementById('admin-modal').style.display = 'flex';
}
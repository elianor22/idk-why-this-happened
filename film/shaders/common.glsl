#define PI 3.14159265359
#define TAU 6.28318530718
uniform vec2 uRes;
uniform float uTime;
uniform int uFrame;

uint hashu(uvec3 v){
    v = v * 1664525u + 1013904223u;
    v.x += v.y * v.z; v.y += v.z * v.x; v.z += v.x * v.y;
    v ^= v >> 16u;
    v.x += v.y * v.z; v.y += v.z * v.x; v.z += v.x * v.y;
    return v.x ^ v.y ^ v.z;
}
float h13(ivec3 p){ return float(hashu(uvec3(p))) * (1.0/4294967296.0); }
float h12(ivec2 p){ return float(hashu(uvec3(uvec2(p), 7u))) * (1.0/4294967296.0); }
float h11(int n){ return float(hashu(uvec3(uint(n), 3u, 11u))) * (1.0/4294967296.0); }
vec2 h22(ivec2 p){ uint a = hashu(uvec3(uvec2(p), 1u)); uint b = hashu(uvec3(uvec2(p), 2u)); return vec2(a, b) * (1.0/4294967296.0); }
vec3 h33(ivec3 p){ return vec3(hashu(uvec3(p)+uvec3(0u,0u,1u)), hashu(uvec3(p)+uvec3(1u,5u,2u)), hashu(uvec3(p)+uvec3(9u,3u,3u))) * (1.0/4294967296.0); }
float hf(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123); }

vec3 grad3(ivec3 p){ return normalize(h33(p) * 2.0 - 1.0 + 1e-4); }

float gnoise(vec3 x){
    ivec3 i = ivec3(floor(x)); vec3 f = fract(x);
    vec3 u = f*f*f*(f*(f*6.0-15.0)+10.0);
    float a = dot(grad3(i+ivec3(0,0,0)), f-vec3(0,0,0));
    float b = dot(grad3(i+ivec3(1,0,0)), f-vec3(1,0,0));
    float c = dot(grad3(i+ivec3(0,1,0)), f-vec3(0,1,0));
    float d = dot(grad3(i+ivec3(1,1,0)), f-vec3(1,1,0));
    float e = dot(grad3(i+ivec3(0,0,1)), f-vec3(0,0,1));
    float g = dot(grad3(i+ivec3(1,0,1)), f-vec3(1,0,1));
    float h = dot(grad3(i+ivec3(0,1,1)), f-vec3(0,1,1));
    float k = dot(grad3(i+ivec3(1,1,1)), f-vec3(1,1,1));
    return mix(mix(mix(a,b,u.x), mix(c,d,u.x), u.y), mix(mix(e,g,u.x), mix(h,k,u.x), u.y), u.z) * 1.15;
}
float vnoise(vec3 x){
    ivec3 i = ivec3(floor(x)); vec3 f = fract(x);
    vec3 u = f*f*(3.0-2.0*f);
    float a = h13(i), b = h13(i+ivec3(1,0,0)), c = h13(i+ivec3(0,1,0)), d = h13(i+ivec3(1,1,0));
    float e = h13(i+ivec3(0,0,1)), g = h13(i+ivec3(1,0,1)), h = h13(i+ivec3(0,1,1)), k = h13(i+ivec3(1,1,1));
    return mix(mix(mix(a,b,u.x), mix(c,d,u.x), u.y), mix(mix(e,g,u.x), mix(h,k,u.x), u.y), u.z);
}
float fbm(vec3 p, int oct){
    float a = 0.5, s = 0.0;
    for (int i = 0; i < oct; i++){ s += a * gnoise(p); p = p * 2.02 + vec3(1.7, 9.2, 4.1); a *= 0.5; }
    return s;
}
float fbmv(vec3 p, int oct){
    float a = 0.5, s = 0.0;
    for (int i = 0; i < oct; i++){ s += a * vnoise(p); p = p * 2.03 + vec3(3.1, 1.3, 7.7); a *= 0.5; }
    return s;
}
// ridged
float rfbm(vec3 p, int oct){
    float a = 0.5, s = 0.0;
    for (int i = 0; i < oct; i++){ float n = 1.0 - abs(gnoise(p)); s += a * n * n; p = p * 2.1 + vec3(5.3, 2.2, 8.8); a *= 0.5; }
    return s;
}
// voronoi: returns (F1, F2, id-hash)
vec3 voronoi(vec2 x, float t){
    ivec2 n = ivec2(floor(x)); vec2 f = fract(x);
    float f1 = 8.0, f2 = 8.0, id = 0.0;
    for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++){
        ivec2 g = ivec2(i, j);
        vec2 o = h22(n + g);
        o = 0.5 + 0.5 * sin(t + TAU * o);
        vec2 r = vec2(g) + o - f;
        float d = dot(r, r);
        if (d < f1){ f2 = f1; f1 = d; id = h12(n+g); }
        else if (d < f2){ f2 = d; }
    }
    return vec3(sqrt(f1), sqrt(f2), id);
}
mat2 rot(float a){ float c = cos(a), s = sin(a); return mat2(c, -s, s, c); }
float sat(float x){ return clamp(x, 0.0, 1.0); }
float sstep(float a, float b, float x){ return smoothstep(a, b, x); }
float lin(float a, float b, float x){ return clamp((x-a)/(b-a), 0.0, 1.0); }
float easeOut3(float x){ x = clamp(x,0.0,1.0); return 1.0 - pow(1.0 - x, 3.0); }
float easeIO(float x){ x = clamp(x,0.0,1.0); return 0.5 - 0.5*cos(PI*x); }
vec3 blackbody(float k){ // k in 0..1 -> deep red .. orange .. yellow-white
    vec3 c = vec3(1.0, 0.18, 0.02) * sstep(0.0, 0.25, k);
    c = mix(c, vec3(1.0, 0.52, 0.08), sstep(0.2, 0.55, k));
    c = mix(c, vec3(1.0, 0.86, 0.50), sstep(0.5, 0.85, k));
    c = mix(c, vec3(1.0, 0.97, 0.90), sstep(0.8, 1.0, k));
    return c;
}
vec3 pal(float t, vec3 a, vec3 b, vec3 c, vec3 d){ return a + b * cos(TAU * (c * t + d)); }
float luma(vec3 c){ return dot(c, vec3(0.2126, 0.7152, 0.0722)); }
// distance to segment
float sdSeg(vec2 p, vec2 a, vec2 b){ vec2 pa = p-a, ba = b-a; float h = clamp(dot(pa,ba)/dot(ba,ba), 0.0, 1.0); return length(pa - ba*h); }
float sdRing(vec2 p, vec2 c, float r){ return abs(length(p-c) - r); }

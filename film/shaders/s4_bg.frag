#version 430
uniform vec2 uGlowC;
uniform float uGlowA;
uniform vec2 uGlow2C;
uniform float uGlow2A;
uniform float uFadeIn;
uniform vec2 uCamP;
uniform float uWhite;
out vec4 o;
void main(){
    vec2 uv = (gl_FragCoord.xy - 0.5 * uRes) / uRes.y;
    float t = uTime;
    vec3 col = vec3(0.0015, 0.006, 0.009);
    float r = length(uv);
    col += vec3(0.004, 0.016, 0.022) * exp(-r * 1.6);
    // slow volumetric fog drifting
    vec3 P = vec3(uv * 1.6 + uCamP * 0.06, t * 0.03);
    float f = fbm(P, 5) * 0.5 + 0.5;
    float f2 = fbm(P * 2.2 + 5.0, 4) * 0.5 + 0.5;
    col += vec3(0.010, 0.034, 0.042) * pow(f, 2.4) * 0.35 + vec3(0.025, 0.010, 0.035) * pow(f2, 3.0) * 0.25;
    // glow bounce from the travelling impulse
    float g1 = length(uv - uGlowC);
    col += vec3(0.05, 0.38, 0.34) * exp(-g1 * 3.2) * uGlowA * (0.5 + 0.8 * f) * 0.6;
    float g2 = length(uv - uGlow2C);
    col += vec3(0.55, 0.16, 0.50) * exp(-g2 * 2.0) * uGlow2A * (0.5 + 0.8 * f2) * 0.30;
    col *= uFadeIn;
    col += vec3(1.0, 0.97, 0.98) * uWhite;
    o = vec4(col, 1.0);
}

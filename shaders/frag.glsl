#version 330 core

uniform uint bitmap[938];
uniform vec3 set_color;
uniform vec3 unset_color;

in vec2 uvs;
out vec4 f_color;

void main() {
    int delta = int(uvs.x * 200.0) + 200 * int(uvs.y * 150.0);
    uint segment = bitmap[int(delta / 32)];
    uint data = (segment >> (delta % 32)) & 1u;
    float set_factor = float(data);
    f_color = vec4((set_color / 255.) * set_factor + (unset_color / 255.) * (1.0 - set_factor), 1.0);
}

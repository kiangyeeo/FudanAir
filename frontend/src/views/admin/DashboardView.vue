<template>
  <div class="dashboard">
    <section class="page-section">
      <h1 class="page-title">管理概览</h1>
      <el-row :gutter="12">
        <el-col :span="6"><el-statistic title="城市" :value="0" /></el-col>
        <el-col :span="6"><el-statistic title="机场" :value="0" /></el-col>
        <el-col :span="6"><el-statistic title="航班" :value="0" /></el-col>
        <el-col :span="6"><el-statistic title="订单" :value="0" /></el-col>
      </el-row>
    </section>
    <section class="page-section">
      <h2>待接入模块</h2>
      <el-table :data="[]" border>
        <el-table-column prop="module" label="模块" />
        <el-table-column prop="status" label="状态" />
      </el-table>
    </section>
  </div>
</template>

<style scoped>
.dashboard {
  display: grid;
  gap: 16px;
}

h2 {
  margin: 0 0 12px;
  font-size: 16px;
}
</style>
